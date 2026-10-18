"""Diseases, disease cases, treatments, feedings and reminder tasks (stage 3).

Rules that keep hive state consistent live here:
- a hive with an open CONFIRMED/TREATING case is SICK (QUARANTINE for quarantine diseases);
  it returns to ACTIVE when no such case remains;
- next treatment / feeding dates create reminders; a new record closes the older open ones.
"""
import re
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    ARCHIVED_HIVE_STATUSES,
    Disease,
    Feeding,
    Hive,
    HiveDisease,
    HiveStatus,
    Task,
    Treatment,
    User,
)
from app.models.enums import (
    ACTIVE_CASE_STATUSES,
    CASE_STATUS_ORDER,
    DiseaseCaseStatus,
    TaskKind,
    TaskStatus,
)
from app.schemas.common import today
from app.schemas.health import (
    CaseCreate,
    CaseUpdate,
    DiseaseCreate,
    FeedingCreate,
    FeedingUpdate,
    TreatmentCreate,
    TreatmentUpdate,
)
from app.services import audit_service as audit
from app.services import stock_service
from app.utils.errors import ConflictError, NotFoundError, ValidationFailed

# Statuses the disease rule may switch between; manual statuses (WEAK, QUEENLESS…) are left alone
_HEALTH_DRIVEN = frozenset({HiveStatus.SICK, HiveStatus.QUARANTINE})
_LIVING = frozenset({HiveStatus.ACTIVE, HiveStatus.STRONG, HiveStatus.WEAK, HiveStatus.QUEENLESS,
                     HiveStatus.SICK, HiveStatus.QUARANTINE})


# ---------- guards ----------

def already_saved(db: Session, model, client_uid: uuid.UUID | None, hive_id: uuid.UUID):
    """A record sent again from the phone's offline queue (same client_uid): return the saved one."""
    if client_uid is None:
        return None
    existing = db.scalar(select(model).where(model.client_uid == client_uid))
    if existing is not None and existing.hive_id != hive_id:
        raise ConflictError("Эта запись уже сохранена для другого улья")
    return existing


def get_hive_for_record(db: Session, hive_id: uuid.UUID, *, require_family: bool = True) -> Hive:
    hive = db.get(Hive, hive_id)
    if hive is None:
        raise NotFoundError("Улей не найден")
    if hive.status in ARCHIVED_HIVE_STATUSES:
        raise ConflictError(f"Улей №{hive.hive_number} в архиве — новые записи не добавляются")
    if require_family and hive.current_family_id is None:
        raise ConflictError(f"В улье №{hive.hive_number} нет пчелиной семьи")
    return hive


def _get(db: Session, model, obj_id: uuid.UUID, message: str):
    obj = db.get(model, obj_id)
    if obj is None:
        raise NotFoundError(message)
    return obj


# ---------- tasks ----------

def create_task(db: Session, *, hive: Hive, kind: TaskKind, title: str, due: date, user: User,
                source_type: str, source_id: uuid.UUID) -> Task:
    task = Task(hive_id=hive.id, kind=kind, title=title, due_date=due, status=TaskStatus.OPEN,
                source_type=source_type, source_id=source_id, created_by=user.id)
    db.add(task)
    return task


def close_open_tasks(db: Session, hive_id: uuid.UUID, kind: TaskKind, user: User) -> int:
    tasks = db.scalars(select(Task).where(Task.hive_id == hive_id, Task.kind == kind,
                                          Task.status == TaskStatus.OPEN)).all()
    now = datetime.now(timezone.utc)
    for t in tasks:
        t.status, t.completed_at, t.completed_by = TaskStatus.DONE, now, user.id
    return len(tasks)


def complete_task(db: Session, task_id: uuid.UUID, user: User) -> Task:
    task = _get(db, Task, task_id, "Напоминание не найдено")
    if task.status != TaskStatus.OPEN:
        raise ConflictError("Напоминание уже закрыто")
    task.status, task.completed_at, task.completed_by = TaskStatus.DONE, datetime.now(timezone.utc), user.id
    audit.record(db, user=user, entity_type="task", entity_id=task.id, hive_id=task.hive_id,
                 action="task_done", new={"title": task.title})
    db.commit()
    return task


def list_tasks(db: Session, *, status: TaskStatus | None, hive_id: uuid.UUID | None,
               due_before: date | None, limit: int = 200) -> list[tuple[Task, str | None]]:
    stmt = select(Task, Hive.hive_number).outerjoin(Hive, Task.hive_id == Hive.id)
    if status:
        stmt = stmt.where(Task.status == status)
    if hive_id:
        stmt = stmt.where(Task.hive_id == hive_id)
    if due_before:
        stmt = stmt.where(Task.due_date <= due_before)
    return list(db.execute(stmt.order_by(Task.due_date, Task.created_at).limit(limit)).all())


# ---------- hive health status ----------

def sync_hive_health_status(db: Session, hive: Hive, user: User, comment: str | None = None) -> None:
    """Derive SICK / QUARANTINE / ACTIVE from the hive's open disease cases (FR-010)."""
    db.flush()
    open_cases = db.scalars(
        select(HiveDisease).where(HiveDisease.hive_id == hive.id, HiveDisease.status.in_(ACTIVE_CASE_STATUSES))
    ).unique().all()
    if open_cases:
        target = HiveStatus.QUARANTINE if any(c.disease.is_quarantine for c in open_cases) else HiveStatus.SICK
        if hive.status not in _LIVING or hive.status == target:
            return
    else:
        if hive.status not in _HEALTH_DRIVEN:
            return
        target = HiveStatus.ACTIVE
    old = hive.status
    hive.status = target
    hive.version += 1
    audit.record(db, user=user, entity_type="hive", entity_id=hive.id, hive_id=hive.id, action="health_status",
                 old={"status": old.value}, new={"status": target.value}, comment=comment)


# ---------- disease catalog ----------

def list_diseases(db: Session, include_inactive: bool = False) -> list[Disease]:
    stmt = select(Disease).order_by(Disease.sort_order, Disease.name)
    if not include_inactive:
        stmt = stmt.where(Disease.is_active.is_(True))
    return list(db.scalars(stmt))


def create_disease(db: Session, data: DiseaseCreate, user: User) -> Disease:
    if db.scalar(select(Disease.id).where(func.lower(Disease.name) == data.name.lower())):
        raise ConflictError(f"Болезнь «{data.name}» уже есть в справочнике")
    base = re.sub(r"[^A-Z0-9]+", "_", data.name.upper()).strip("_")[:20] or "CUSTOM"
    code = f"CUSTOM_{base}_{uuid.uuid4().hex[:6].upper()}"
    disease = Disease(code=code, name=data.name, is_quarantine=data.is_quarantine, is_active=True, sort_order=500)
    db.add(disease)
    db.flush()
    audit.record(db, user=user, entity_type="disease", entity_id=disease.id, action="created",
                 new={"name": disease.name, "is_quarantine": disease.is_quarantine})
    db.commit()
    return disease


# ---------- disease cases ----------

def _check_case_dates(status: DiseaseCaseStatus, detected: date, resolved: date | None) -> None:
    if status == DiseaseCaseStatus.RESOLVED and resolved is None:
        raise ValidationFailed("Укажите дату выздоровления")
    if status != DiseaseCaseStatus.RESOLVED and resolved is not None:
        raise ValidationFailed("Дата выздоровления указывается только для вылеченной болезни")
    if resolved and resolved < detected:
        raise ValidationFailed("Дата выздоровления раньше даты обнаружения")


def create_case(db: Session, hive_id: uuid.UUID, data: CaseCreate, user: User) -> tuple[HiveDisease, Hive]:
    hive = get_hive_for_record(db, hive_id)
    disease = _get(db, Disease, data.disease_id, "Болезнь не найдена в справочнике")
    if not disease.is_active:
        raise ConflictError("Эта болезнь больше не используется в справочнике")
    detected = data.detected_at or today()
    _check_case_dates(data.status, detected, data.resolved_at)
    case = HiveDisease(hive_id=hive.id, disease_id=disease.id, detected_at=detected, severity=data.severity,
                       status=data.status, symptoms=data.symptoms, diagnosis=data.diagnosis, notes=data.notes,
                       resolved_at=data.resolved_at, created_by=user.id)
    db.add(case)
    db.flush()
    audit.record(db, user=user, entity_type="hive_disease", entity_id=case.id, hive_id=hive.id,
                 action="disease_opened", new={"disease": disease.name, "status": case.status.value,
                                               "severity": case.severity.value})
    sync_hive_health_status(db, hive, user, comment=disease.name)
    db.commit()
    db.refresh(hive)
    return case, hive


def update_case(db: Session, case_id: uuid.UUID, data: CaseUpdate, user: User) -> tuple[HiveDisease, Hive]:
    case = _get(db, HiveDisease, case_id, "Запись о болезни не найдена")
    hive = get_hive_for_record(db, case.hive_id, require_family=False)
    changes = data.model_dump(exclude_unset=True, exclude={"comment"})
    new_status = changes.get("status", case.status)
    if case.status == DiseaseCaseStatus.RESOLVED and set(changes) - {"notes", "diagnosis", "symptoms"}:
        raise ConflictError("Болезнь уже отмечена вылеченной. Если она вернулась — откройте новую запись.")
    if CASE_STATUS_ORDER[new_status] < CASE_STATUS_ORDER[case.status]:
        raise ConflictError("Статус болезни нельзя вернуть назад")
    if new_status == DiseaseCaseStatus.RESOLVED and "resolved_at" not in changes and case.resolved_at is None:
        changes["resolved_at"] = today()
    _check_case_dates(new_status, case.detected_at, changes.get("resolved_at", case.resolved_at))

    before = audit.snapshot(case, ["status", "severity", "symptoms", "diagnosis", "notes", "resolved_at"])
    for k, v in changes.items():
        setattr(case, k, v)
    old, new = audit.diff(before, audit.snapshot(case, list(before)))
    if new:
        action = "disease_resolved" if new.get("status") == DiseaseCaseStatus.RESOLVED.value else "disease_updated"
        audit.record(db, user=user, entity_type="hive_disease", entity_id=case.id, hive_id=hive.id,
                     action=action, old=old, new={**new, "disease": case.disease.name}, comment=data.comment)
        sync_hive_health_status(db, hive, user, comment=case.disease.name)
    db.commit()
    db.refresh(hive)
    return case, hive


def list_cases(db: Session, hive_id: uuid.UUID) -> list[HiveDisease]:
    rows = db.scalars(select(HiveDisease).where(HiveDisease.hive_id == hive_id)
                      .order_by(HiveDisease.detected_at.desc(), HiveDisease.created_at.desc())).unique().all()
    return sorted(rows, key=lambda c: c.status == DiseaseCaseStatus.RESOLVED)  # open cases first


# ---------- treatments ----------

def _resolve_treatment_links(db: Session, hive: Hive, data) -> tuple[uuid.UUID | None, HiveDisease | None]:
    case = None
    disease_id = data.disease_id
    if data.hive_disease_id:
        case = _get(db, HiveDisease, data.hive_disease_id, "Запись о болезни не найдена")
        if case.hive_id != hive.id:
            raise ConflictError("Эта болезнь записана в другом улье")
        if disease_id and disease_id != case.disease_id:
            raise ValidationFailed("Болезнь не совпадает с выбранной записью о болезни")
        disease_id = case.disease_id
    elif disease_id:
        _get(db, Disease, disease_id, "Болезнь не найдена в справочнике")
    return disease_id, case


def _treatment_reminder(db, hive, treatment, user):
    close_open_tasks(db, hive.id, TaskKind.TREATMENT, user)
    if treatment.next_treatment_date:
        title = f"Повторная обработка: {treatment.medication}"
        create_task(db, hive=hive, kind=TaskKind.TREATMENT, title=title, due=treatment.next_treatment_date,
                    user=user, source_type="treatment", source_id=treatment.id)


def create_treatment(db: Session, hive_id: uuid.UUID, data: TreatmentCreate, user: User) -> tuple[Treatment, Hive]:
    if (done := already_saved(db, Treatment, data.client_uid, hive_id)) is not None:
        return done, db.get(Hive, hive_id)
    hive = get_hive_for_record(db, hive_id)
    disease_id, case = _resolve_treatment_links(db, hive, data)
    if case and case.status == DiseaseCaseStatus.RESOLVED:
        raise ConflictError("Эта болезнь уже вылечена")
    stock_item = stock_service.check_treatment_item(db, data.stock_item_id)
    fields = data.model_dump(exclude={"disease_id", "hive_disease_id", "treated_at", "stock_item_id", "stock_quantity"})
    treatment = Treatment(hive_id=hive.id, disease_id=disease_id, hive_disease_id=case.id if case else None,
                          treated_at=data.treated_at or today(), performed_by=user.id, **fields)
    db.add(treatment)
    db.flush()
    _treatment_reminder(db, hive, treatment, user)
    stock_service.sync_treatment(db, treatment, hive, stock_item, data.stock_quantity, user)
    if case and case.status in (DiseaseCaseStatus.SUSPECTED, DiseaseCaseStatus.CONFIRMED):
        old = case.status
        case.status = DiseaseCaseStatus.TREATING
        audit.record(db, user=user, entity_type="hive_disease", entity_id=case.id, hive_id=hive.id,
                     action="disease_updated", old={"status": old.value},
                     new={"status": case.status.value, "disease": case.disease.name}, comment="Начато лечение")
        sync_hive_health_status(db, hive, user, comment=case.disease.name)
    db.commit()
    db.refresh(treatment)
    db.refresh(hive)
    return treatment, hive


def update_treatment(db: Session, treatment_id: uuid.UUID, data: TreatmentUpdate, user: User) -> tuple[Treatment, Hive]:
    treatment = _get(db, Treatment, treatment_id, "Обработка не найдена")
    hive = get_hive_for_record(db, treatment.hive_id, require_family=False)
    disease_id, case = _resolve_treatment_links(db, hive, data)
    fields = ["treated_at", "medication", "dosage", "method", "result", "next_treatment_date", "notes",
              "disease_id", "hive_disease_id"]
    before = audit.snapshot(treatment, fields)
    stock_item = stock_service.check_treatment_item(db, data.stock_item_id) if data.stock_item_id else None
    values = data.model_dump(exclude={"comment", "stock_item_id", "stock_quantity"})
    values["treated_at"] = values["treated_at"] or treatment.treated_at
    values["disease_id"], values["hive_disease_id"] = disease_id, case.id if case else None
    if values["next_treatment_date"] and values["next_treatment_date"] < values["treated_at"]:
        raise ValidationFailed("Следующая обработка не может быть раньше этой")
    for k in fields:
        setattr(treatment, k, values[k])
    old, new = audit.diff(before, audit.snapshot(treatment, fields))
    if new:
        audit.record(db, user=user, entity_type="treatment", entity_id=treatment.id, hive_id=hive.id,
                     action="corrected", old=old, new=new, comment=data.comment)
        if "next_treatment_date" in new:
            _retarget_task(db, treatment.id, "treatment", treatment.next_treatment_date, hive, user,
                           TaskKind.TREATMENT, f"Повторная обработка: {treatment.medication}")
    stock_service.sync_treatment(db, treatment, hive, stock_item, data.stock_quantity, user)
    db.commit()
    db.refresh(treatment)
    return treatment, hive


def _retarget_task(db, source_id, source_type, due, hive, user, kind, title):
    task = db.scalar(select(Task).where(Task.source_id == source_id, Task.source_type == source_type,
                                        Task.status == TaskStatus.OPEN))
    if task and due:
        task.due_date = due
    elif task and not due:
        task.status = TaskStatus.CANCELLED
    elif due:
        create_task(db, hive=hive, kind=kind, title=title, due=due, user=user,
                    source_type=source_type, source_id=source_id)


def list_treatments(db: Session, hive_id: uuid.UUID) -> list[Treatment]:
    return list(db.scalars(select(Treatment).where(Treatment.hive_id == hive_id)
                           .order_by(Treatment.treated_at.desc(), Treatment.created_at.desc())).unique())


# ---------- feedings ----------

def _feeding_title(f: Feeding) -> str:
    from app.utils.labels import FEED_TYPE
    return f"Подкормка: {FEED_TYPE[f.feed_type].lower()}"


def create_feeding(db: Session, hive_id: uuid.UUID, data: FeedingCreate, user: User) -> tuple[Feeding, Hive]:
    if (done := already_saved(db, Feeding, data.client_uid, hive_id)) is not None:
        return done, db.get(Hive, hive_id)
    hive = get_hive_for_record(db, hive_id)
    feeding = Feeding(hive_id=hive.id, created_by=user.id, **data.model_dump(exclude={"fed_at"}),
                      fed_at=data.fed_at or today())
    db.add(feeding)
    db.flush()
    stock_service.sync_feeding(db, feeding, hive, user)
    close_open_tasks(db, hive.id, TaskKind.FEEDING, user)
    if feeding.next_feeding_date:
        create_task(db, hive=hive, kind=TaskKind.FEEDING, title=_feeding_title(feeding),
                    due=feeding.next_feeding_date, user=user, source_type="feeding", source_id=feeding.id)
    db.commit()
    db.refresh(feeding)
    db.refresh(hive)
    return feeding, hive


def update_feeding(db: Session, feeding_id: uuid.UUID, data: FeedingUpdate, user: User) -> tuple[Feeding, Hive]:
    feeding = _get(db, Feeding, feeding_id, "Подкормка не найдена")
    hive = get_hive_for_record(db, feeding.hive_id, require_family=False)
    fields = ["fed_at", "feed_type", "quantity", "unit", "reason", "result", "next_feeding_date", "notes"]
    before = audit.snapshot(feeding, fields)
    values = data.model_dump(exclude={"comment"})
    values["fed_at"] = values["fed_at"] or feeding.fed_at
    if values["next_feeding_date"] and values["next_feeding_date"] < values["fed_at"]:
        raise ValidationFailed("Следующая подкормка не может быть раньше этой")
    for k in fields:
        setattr(feeding, k, values[k])
    old, new = audit.diff(before, audit.snapshot(feeding, fields))
    if new:
        audit.record(db, user=user, entity_type="feeding", entity_id=feeding.id, hive_id=hive.id,
                     action="corrected", old=old, new=new, comment=data.comment)
        if "next_feeding_date" in new:
            _retarget_task(db, feeding.id, "feeding", feeding.next_feeding_date, hive, user,
                           TaskKind.FEEDING, _feeding_title(feeding))
        stock_service.sync_feeding(db, feeding, hive, user)
    db.commit()
    db.refresh(feeding)
    return feeding, hive


def list_feedings(db: Session, hive_id: uuid.UUID) -> list[Feeding]:
    return list(db.scalars(select(Feeding).where(Feeding.hive_id == hive_id)
                           .order_by(Feeding.fed_at.desc(), Feeding.created_at.desc())).unique())


# ---------- attention (home screen) ----------

def attention(db: Session) -> dict[str, int]:
    from app.models import ARCHIVED_HIVE_STATUSES as ARCH
    now = datetime.now(timezone.utc)
    t = today()
    living = select(Hive.id).where(Hive.status.not_in(ARCH), Hive.current_family_id.is_not(None))
    needs = db.scalar(select(func.count()).select_from(
        living.where((Hive.next_inspection_at.is_(None) & Hive.last_inspection_at.is_(None))
                     | (Hive.next_inspection_at <= now)).subquery())) or 0
    open_tasks = db.scalar(select(func.count()).select_from(Task).where(Task.status == TaskStatus.OPEN)) or 0
    overdue = db.scalar(select(func.count()).select_from(Task).where(Task.status == TaskStatus.OPEN,
                                                                     Task.due_date < t)) or 0
    sick = db.scalar(select(func.count()).select_from(Hive).where(
        Hive.status.in_([HiveStatus.SICK, HiveStatus.QUARANTINE]))) or 0
    return {"needs_inspection": needs, "open_tasks": open_tasks, "overdue_tasks": overdue, "sick": sick}
