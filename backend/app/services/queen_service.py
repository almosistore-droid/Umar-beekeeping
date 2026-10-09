"""Queens: registry, installation into hives, replacement and removal with full history."""
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ARCHIVED_HIVE_STATUSES,
    REMOVED_QUEEN_STATUSES,
    Hive,
    HiveStatus,
    Queen,
    QueenAssignment,
    QueenStatus,
    User,
)
from app.repositories import hive_repository as repo
from app.schemas.common import today
from app.schemas.queen import (
    MARKING_COLORS,
    AssignQueenRequest,
    HiveRef,
    QueenAssignmentOut,
    QueenBrief,
    QueenCreate,
    QueenOut,
    QueenUpdate,
    RemoveQueenRequest,
)
from app.services import audit_service as audit
from app.utils.age import age_in_months, age_label
from app.utils.errors import ConflictError, NotFoundError, ValidationFailed

# Statuses that describe a living hive with a family; queen events adjust between these
LIVING_HIVE_STATUSES = frozenset(
    {HiveStatus.ACTIVE, HiveStatus.WEAK, HiveStatus.STRONG, HiveStatus.SICK,
     HiveStatus.QUEENLESS, HiveStatus.QUARANTINE}
)


# ---------- reading ----------

def get_queen(db: Session, queen_id: uuid.UUID) -> Queen:
    queen = db.get(Queen, queen_id)
    if queen is None:
        raise NotFoundError("Матка не найдена")
    return queen


def to_brief(queen: Queen | None, on: date | None = None) -> QueenBrief | None:
    if queen is None:
        return None
    on = on or today()
    return QueenBrief(
        id=queen.id, queen_code=queen.queen_code, status=queen.status,
        birth_date=queen.birth_date, birth_year=queen.birth_year,
        age_months=age_in_months(queen.birth_date, queen.birth_year, on),
        age_label=age_label(queen.birth_date, queen.birth_year, on),
        breed=queen.breed, marking_color=queen.marking_color, installed_at=queen.installed_at,
    )


def to_out(queen: Queen, hive: Hive | None) -> QueenOut:
    on = today()
    data = {c: getattr(queen, c) for c in QueenOut.model_fields if hasattr(queen, c) and c != "current_hive"}
    data["age_months"] = age_in_months(queen.birth_date, queen.birth_year, on)
    data["age_label"] = age_label(queen.birth_date, queen.birth_year, on)
    data["current_hive"] = (
        HiveRef(id=hive.id, hive_number=hive.hive_number, apiary_name=hive.apiary.name) if hive else None
    )
    return QueenOut(**data)


def to_out_many(db: Session, queens: list[Queen]) -> list[QueenOut]:
    hives = repo.hives_by_ids(db, {q.current_hive_id for q in queens if q.current_hive_id})
    return [to_out(q, hives.get(q.current_hive_id)) for q in queens]


def assignment_out(a: QueenAssignment, hive_number: str) -> QueenAssignmentOut:
    return QueenAssignmentOut(
        id=a.id, queen_id=a.queen_id, queen_code=a.queen.queen_code, hive_id=a.hive_id,
        hive_number=hive_number, installed_at=a.installed_at, removed_at=a.removed_at,
        removal_reason=a.removal_reason,
    )


def queen_history(db: Session, queen: Queen) -> list[QueenAssignmentOut]:
    items = repo.list_queen_assignments(db, queen.id)
    hives = repo.hives_by_ids(db, {a.hive_id for a in items})
    return [assignment_out(a, hives[a.hive_id].hive_number) for a in items]


# ---------- writing ----------

def _ensure_code_free(db: Session, code: str, exclude: uuid.UUID | None = None) -> None:
    stmt = select(Queen.id).where(Queen.queen_code == code)
    if exclude:
        stmt = stmt.where(Queen.id != exclude)
    if db.scalar(stmt):
        raise ConflictError(f"Матка с кодом {code} уже есть")


def _bump(hive: Hive) -> None:
    hive.version += 1


def create_queen(db: Session, data: QueenCreate, user: User) -> Queen:
    _ensure_code_free(db, data.queen_code)
    fields = data.model_dump(exclude={"hive_id", "installed_at"})
    if not fields.get("marking_color") and fields.get("birth_year"):
        fields["marking_color"] = MARKING_COLORS[fields["birth_year"] % 10]
    queen = Queen(**fields)
    db.add(queen)
    db.flush()
    audit.record(db, user=user, entity_type="queen", entity_id=queen.id, action="created",
                 new=audit.snapshot(queen))
    if data.hive_id:
        hive = db.get(Hive, data.hive_id)
        if hive is None:
            raise NotFoundError("Улей не найден")
        assign_queen(db, hive, AssignQueenRequest(queen_id=queen.id, installed_at=data.installed_at), user,
                     commit=False)
    db.commit()
    db.refresh(queen)
    return queen


def update_queen(db: Session, queen: Queen, data: QueenUpdate, user: User) -> Queen:
    changes = data.model_dump(exclude_unset=True, exclude={"comment"})
    if "queen_code" in changes and changes["queen_code"] != queen.queen_code:
        _ensure_code_free(db, changes["queen_code"], exclude=queen.id)

    new_status = changes.get("status")
    if new_status in REMOVED_QUEEN_STATUSES and queen.current_hive_id:
        raise ConflictError("Матка сейчас в улье. Чтобы списать её, используйте «Убрать матку» в карточке улья.")
    if new_status and new_status not in REMOVED_QUEEN_STATUSES and queen.status in REMOVED_QUEEN_STATUSES:
        raise ConflictError("Выбывшую матку нельзя вернуть в работу. Если это ошибка — создайте запись заново.")

    # Birth date / year must stay consistent together with existing values
    birth_date = changes.get("birth_date", queen.birth_date)
    birth_year = changes.get("birth_year", queen.birth_year)
    if "birth_date" in changes and changes["birth_date"] and "birth_year" not in changes:
        birth_year = changes["birth_year"] = changes["birth_date"].year
    if birth_date and birth_year and birth_date.year != birth_year:
        raise ValidationFailed("Год рождения не совпадает с датой рождения")
    if birth_date and queen.installed_at and birth_date > queen.installed_at:
        raise ValidationFailed("Дата рождения позже даты подсадки в улей")

    before = audit.snapshot(queen)
    for key, value in changes.items():
        setattr(queen, key, value)
    if new_status in REMOVED_QUEEN_STATUSES and queen.removed_at is None:
        queen.removed_at = today()
    old, new = audit.diff(before, audit.snapshot(queen))
    if new:
        audit.record(db, user=user, entity_type="queen", entity_id=queen.id, action="updated",
                     old=old, new=new, hive_id=queen.current_hive_id, comment=data.comment)
    db.commit()
    db.refresh(queen)
    return queen


def _detach(db: Session, queen: Queen, hive: Hive, *, status: QueenStatus, when: date,
            reason: str | None) -> None:
    """Take a queen out of a hive and close her assignment period."""
    if queen.installed_at and when < queen.installed_at:
        raise ValidationFailed("Дата выбытия раньше даты подсадки")
    assignment = repo.open_assignment(db, queen.id)
    if assignment:
        assignment.removed_at = when
        assignment.removal_reason = reason
    queen.current_hive_id = None
    if status in REMOVED_QUEEN_STATUSES:
        queen.status = status
        queen.removed_at = when
        queen.removal_reason = reason
    hive.current_queen_id = None
    if hive.status in LIVING_HIVE_STATUSES and hive.current_family_id:
        hive.status = HiveStatus.QUEENLESS
    _bump(hive)
    db.flush()  # free the "one queen per hive" slot before another queen takes it


def assign_queen(db: Session, hive: Hive, data: AssignQueenRequest, user: User, *, commit: bool = True) -> Hive:
    when = data.installed_at or today()
    if hive.status in ARCHIVED_HIVE_STATUSES:
        raise ConflictError("Улей в архиве — в него нельзя подсадить матку")
    if hive.current_family_id is None:
        raise ConflictError("В улье нет пчелиной семьи. Сначала заселите семью.")

    queen = get_queen(db, data.queen_id)
    if queen.status in REMOVED_QUEEN_STATUSES:
        raise ConflictError(f"Матка {queen.queen_code} выбыла и не может быть подсажена")
    if queen.current_hive_id == hive.id:
        raise ConflictError(f"Матка {queen.queen_code} уже в этом улье")
    if queen.birth_date and when < queen.birth_date:
        raise ValidationFailed("Дата подсадки раньше даты рождения матки")

    old_code = None
    previous = hive.current_queen
    if previous is not None:
        old_code = previous.queen_code
        _detach(db, previous, hive, status=data.previous_queen_status, when=when,
                reason=data.removal_reason or f"Заменена маткой {queen.queen_code}")

    moved_from = None
    if queen.current_hive_id:
        source = db.get(Hive, queen.current_hive_id)
        moved_from = source.hive_number
        _detach(db, queen, source, status=queen.status, when=when, reason=f"Перенесена в улей №{hive.hive_number}")
        audit.record(db, user=user, entity_type="hive", entity_id=source.id, hive_id=source.id,
                     action="queen_removed", old={"queen_code": queen.queen_code}, new={"queen_code": None},
                     comment=f"Матка перенесена в улей №{hive.hive_number}")

    queen.current_hive_id = hive.id
    queen.installed_at = when
    queen.removed_at = None
    queen.removal_reason = None
    db.add(QueenAssignment(queen_id=queen.id, hive_id=hive.id, installed_at=when, installed_by=user.id))
    hive.current_queen_id = queen.id
    if hive.status == HiveStatus.QUEENLESS:
        hive.status = HiveStatus.ACTIVE
    _bump(hive)

    comment = data.comment
    if moved_from and not comment:
        comment = f"Перенесена из улья №{moved_from}"
    audit.record(db, user=user, entity_type="hive", entity_id=hive.id, hive_id=hive.id,
                 action="queen_replaced" if old_code else "queen_installed",
                 old={"queen_code": old_code} if old_code else None,
                 new={"queen_code": queen.queen_code, "installed_at": when.isoformat()},
                 comment=comment)
    if commit:
        db.commit()
        db.refresh(hive)
    return hive


def remove_queen(db: Session, hive: Hive, data: RemoveQueenRequest, user: User) -> Hive:
    queen = hive.current_queen
    if queen is None:
        raise ConflictError("В улье нет матки")
    when = data.removed_at or today()
    code, old_hive_status = queen.queen_code, hive.status
    _detach(db, queen, hive, status=data.status, when=when, reason=data.reason)
    audit.record(db, user=user, entity_type="hive", entity_id=hive.id, hive_id=hive.id, action="queen_removed",
                 old={"queen_code": code, "status": old_hive_status.value},
                 new={"queen_code": None, "queen_status": data.status.value, "status": hive.status.value},
                 comment=data.reason)
    db.commit()
    db.refresh(hive)
    return hive
