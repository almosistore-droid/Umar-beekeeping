"""Queen rearing calendar.

From the grafting day (day 0, larvae 12–24 h old) the queen develops on a fixed schedule:
accepted cells are visible after a day, cells are sealed on day 5, ripe cells must be moved to mating
nuclei on day 10 (the first queen emerges on day 11–12 and kills the others), queens emerge on day 12,
fly out to mate about a week later and start laying about two weeks after emerging.
Each step becomes a reminder in `tasks` (sent by the bot); marking a step done can record a count.
"""
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from app.models import ARCHIVED_HIVE_STATUSES, Hive, Queen, Task, User
from app.models.enums import TaskKind, TaskStatus
from app.models.rearing import RearingBatch, RearingStatus
from app.schemas.common import today
from app.schemas.rearing import RearingIn, RearingOut, RearingStep, StepDoneIn
from app.services import audit_service as audit
from app.utils.errors import ConflictError, NotFoundError, ValidationFailed


@dataclass(frozen=True)
class Step:
    key: str
    day: int
    title: str
    hint: str
    count_field: str | None = None
    count_label: str | None = None
    reminder: bool = True


STEPS: tuple[Step, ...] = (
    Step("graft", 0, "Прививка личинок", "Личинки 12–24 часов, в мисочки, сразу в семью-воспитательницу.",
         reminder=False),
    Step("acceptance", 1, "Проверить приём личинок",
         "Принятые мисочки отстроены и с молочком. Запишите, сколько принято.", "cells_accepted", "Принято"),
    Step("sealed", 5, "Маточники запечатаны",
         "Не трогайте и не переворачивайте рамку с маточниками. Сосчитайте запечатанные.", "cells_sealed", "Запечатано"),
    Step("move", 10, "Разнести маточники по нуклеусам",
         "Зрелые маточники — по одному в нуклеус или отводок. Завтра выйдут первые матки."),
    Step("emerge", 12, "Выход маток", "Проверьте нуклеусы: сколько маток вышло.", "queens_emerged", "Вышло"),
    Step("mating", 19, "Облёт и спаривание", "Матки облетаются. Не открывайте нуклеусы в середине дня."),
    Step("laying", 26, "Проверить засев",
         "Есть яйца — матка плодная. Запишите, сколько плодных, и добавьте их в «Матки».", "queens_mated", "Плодных"),
)
STEP_BY_KEY = {s.key: s for s in STEPS}
COUNT_ORDER = ("cells_accepted", "cells_sealed", "queens_emerged", "queens_mated")


def _source(step: Step) -> str:
    return f"rearing:{step.key}"


def _get(db: Session, batch_id: uuid.UUID) -> RearingBatch:
    batch = db.get(RearingBatch, batch_id)
    if batch is None:
        raise NotFoundError("Партия вывода маток не найдена")
    return batch


def _tasks(db: Session, batch_id: uuid.UUID) -> dict[str, Task]:
    rows = db.scalars(select(Task).where(Task.source_id == batch_id, Task.source_type.like("rearing:%"))).all()
    return {t.source_type.split(":", 1)[1]: t for t in rows}


def _title(batch: RearingBatch, step: Step) -> str:
    return f"Вывод маток «{batch.label}»: {step.title.lower()}"


def _check_links(db: Session, data: RearingIn) -> None:
    if data.mother_queen_id and db.get(Queen, data.mother_queen_id) is None:
        raise NotFoundError("Матка не найдена")
    if data.cell_builder_hive_id:
        hive = db.get(Hive, data.cell_builder_hive_id)
        if hive is None:
            raise NotFoundError("Улей не найден")
        if hive.status in ARCHIVED_HIVE_STATUSES:
            raise ConflictError(f"Улей №{hive.hive_number} в архиве")


def _check_date(d: date) -> None:
    t = today()
    if d > t:
        raise ValidationFailed("Дата прививки не может быть в будущем")
    if d < t - timedelta(days=60):
        raise ValidationFailed("Прививка была больше 60 дней назад — такую партию записывать уже не нужно")


def _plan_tasks(db: Session, batch: RearingBatch, user: User) -> None:
    """One reminder per step that is still ahead (or today)."""
    existing = _tasks(db, batch.id)
    t = today()
    for step in STEPS:
        if not step.reminder or step.key in existing:
            continue
        due = batch.grafted_at + timedelta(days=step.day)
        if due < t:
            continue
        db.add(Task(hive_id=batch.cell_builder_hive_id, kind=TaskKind.OTHER, title=_title(batch, step), due_date=due,
                    status=TaskStatus.OPEN, source_type=_source(step), source_id=batch.id, created_by=user.id))


def create(db: Session, data: RearingIn, user: User) -> RearingBatch:
    _check_date(data.grafted_at)
    _check_links(db, data)
    count = len(db.scalars(select(RearingBatch.id).where(
        RearingBatch.grafted_at >= date(data.grafted_at.year, 1, 1),
        RearingBatch.grafted_at <= date(data.grafted_at.year, 12, 31))).all())
    batch = RearingBatch(label=data.label or f"Партия {count + 1} · {data.grafted_at.strftime('%d.%m')}",
                         grafted_at=data.grafted_at, cells_grafted=data.cells_grafted,
                         mother_queen_id=data.mother_queen_id, cell_builder_hive_id=data.cell_builder_hive_id,
                         notes=data.notes, created_by=user.id)
    db.add(batch)
    db.flush()
    _plan_tasks(db, batch, user)
    audit.record(db, user=user, entity_type="rearing_batch", entity_id=batch.id, action="created",
                 new={"label": batch.label, "grafted_at": batch.grafted_at.isoformat(), "cells_grafted": batch.cells_grafted})
    db.commit()
    db.refresh(batch)
    return batch


def _active(batch: RearingBatch) -> None:
    if batch.status != RearingStatus.ACTIVE:
        raise ConflictError("Партия уже закрыта")


def update(db: Session, batch_id: uuid.UUID, data: RearingIn, user: User) -> RearingBatch:
    batch = _get(db, batch_id)
    _active(batch)
    _check_date(data.grafted_at)
    _check_links(db, data)
    fields = ["label", "grafted_at", "cells_grafted", "mother_queen_id", "cell_builder_hive_id", "notes"]
    before = audit.snapshot(batch, fields)
    for k in fields:
        value = getattr(data, k)
        if k == "label" and not value:
            continue
        setattr(batch, k, value)
    counts = [getattr(batch, f) for f in COUNT_ORDER if getattr(batch, f) is not None]
    if counts and max(counts) > batch.cells_grafted:
        raise ValidationFailed("Привито меньше, чем уже записано по шагам")
    old, new = audit.diff(before, audit.snapshot(batch, fields))
    if new:
        # the calendar follows the grafting day and the cell-builder hive
        for key, task in _tasks(db, batch.id).items():
            if task.status == TaskStatus.OPEN and key in STEP_BY_KEY:
                task.due_date = batch.grafted_at + timedelta(days=STEP_BY_KEY[key].day)
                task.hive_id = batch.cell_builder_hive_id
                task.title = _title(batch, STEP_BY_KEY[key])
        db.flush()
        _plan_tasks(db, batch, user)
        audit.record(db, user=user, entity_type="rearing_batch", entity_id=batch.id, action="corrected", old=old, new=new)
    db.commit()
    db.refresh(batch)
    return batch


def step_done(db: Session, batch_id: uuid.UUID, key: str, data: StepDoneIn, user: User) -> RearingBatch:
    batch = _get(db, batch_id)
    _active(batch)
    step = STEP_BY_KEY.get(key)
    if step is None or step.key == "graft":
        raise NotFoundError("Такого шага нет")
    if step.count_field:
        if data.count is None:
            raise ValidationFailed(f"Укажите: {step.count_label.lower()}")
        if data.count > batch.cells_grafted:
            raise ValidationFailed(f"Не больше, чем привито ({batch.cells_grafted})")
        i = COUNT_ORDER.index(step.count_field)
        earlier = [getattr(batch, f) for f in COUNT_ORDER[:i] if getattr(batch, f) is not None]
        if earlier and data.count > min(earlier):
            raise ValidationFailed(f"Не может быть больше, чем на прошлом шаге ({min(earlier)})")
        old = getattr(batch, step.count_field)
        setattr(batch, step.count_field, data.count)
    else:
        old = None
    now = datetime.now(timezone.utc)
    task = _tasks(db, batch.id).get(key)
    if task is not None and task.status == TaskStatus.OPEN:
        task.status, task.completed_at, task.completed_by = TaskStatus.DONE, now, user.id
    elif task is None:  # step that was already in the past when the batch was entered
        db.add(Task(hive_id=batch.cell_builder_hive_id, kind=TaskKind.OTHER, title=_title(batch, step),
                    due_date=batch.grafted_at + timedelta(days=step.day), status=TaskStatus.DONE, source_type=_source(step),
                    source_id=batch.id, created_by=user.id, completed_at=now, completed_by=user.id))
    audit.record(db, user=user, entity_type="rearing_batch", entity_id=batch.id, action="step_done",
                 old={step.count_field: old} if step.count_field else None,
                 new={"step": step.title, **({step.count_field: data.count} if step.count_field else {})})
    db.commit()
    db.refresh(batch)
    return batch


def _close(db: Session, batch: RearingBatch, status: RearingStatus, user: User, reason: str | None) -> RearingBatch:
    _active(batch)
    batch.status, batch.finished_at = status, datetime.now(timezone.utc)
    batch.cancel_reason = reason
    for task in _tasks(db, batch.id).values():
        if task.status == TaskStatus.OPEN:
            task.status = TaskStatus.CANCELLED
    audit.record(db, user=user, entity_type="rearing_batch", entity_id=batch.id,
                 action="finished" if status == RearingStatus.DONE else "cancelled",
                 new={"label": batch.label, "queens_mated": batch.queens_mated}, comment=reason)
    db.commit()
    db.refresh(batch)
    return batch


def finish(db: Session, batch_id: uuid.UUID, user: User) -> RearingBatch:
    return _close(db, _get(db, batch_id), RearingStatus.DONE, user, None)


def cancel(db: Session, batch_id: uuid.UUID, reason: str, user: User) -> RearingBatch:
    return _close(db, _get(db, batch_id), RearingStatus.CANCELLED, user, reason.strip())


def to_out(db: Session, batch: RearingBatch) -> RearingOut:
    t = today()
    tasks = _tasks(db, batch.id)
    steps = []
    for s in STEPS:
        d = batch.grafted_at + timedelta(days=s.day)
        task = tasks.get(s.key)
        recorded = s.count_field is not None and getattr(batch, s.count_field) is not None
        if s.key == "graft" or (task is not None and task.status == TaskStatus.DONE) or recorded:
            state = "done"
        elif batch.status != RearingStatus.ACTIVE:
            state = "skipped"
        elif d == t:
            state = "today"
        elif d < t:
            state = "overdue"
        else:
            state = "upcoming"
        steps.append(RearingStep(key=s.key, day=s.day, date=d, title=s.title, hint=s.hint, count_field=s.count_field,
                                 count_label=s.count_label, state=state, task_id=task.id if task else None))
    next_step = next((s for s in steps if s.state in ("overdue", "today", "upcoming")), None)
    return RearingOut(
        id=batch.id, label=batch.label, grafted_at=batch.grafted_at, day=(t - batch.grafted_at).days,
        cells_grafted=batch.cells_grafted, cells_accepted=batch.cells_accepted, cells_sealed=batch.cells_sealed,
        queens_emerged=batch.queens_emerged, queens_mated=batch.queens_mated,
        mother_queen_id=batch.mother_queen_id,
        mother_queen_code=batch.mother_queen.queen_code if batch.mother_queen else None,
        cell_builder_hive_id=batch.cell_builder_hive_id,
        cell_builder_number=batch.cell_builder.hive_number if batch.cell_builder else None,
        status=batch.status, finished_at=batch.finished_at, cancel_reason=batch.cancel_reason, notes=batch.notes,
        next_step=next_step, steps=steps,
    )


def list_batches(db: Session, year: int | None = None) -> list[RearingBatch]:
    stmt = select(RearingBatch)
    if year:
        stmt = stmt.where(RearingBatch.grafted_at >= date(year, 1, 1), RearingBatch.grafted_at <= date(year, 12, 31))
    active_first = case((RearingBatch.status == RearingStatus.ACTIVE, 0), else_=1)
    return list(db.scalars(stmt.order_by(active_first, RearingBatch.grafted_at.desc())).unique())


def get(db: Session, batch_id: uuid.UUID) -> RearingBatch:
    return _get(db, batch_id)
