"""Hives and bee families. Nothing is deleted: families end, hives are archived."""
import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.models import (
    ARCHIVED_HIVE_STATUSES,
    BeeFamily,
    FamilyStatus,
    Hive,
    HiveStatus,
    QueenStatus,
    User,
)
from app.repositories import hive_repository as repo
from app.schemas.apiary import ApiaryBrief
from app.schemas.common import today
from app.schemas.hive import (
    AuditEntryOut,
    EndFamilyRequest,
    FamilyCreate,
    FamilyOut,
    FamilyUpdate,
    HiveCreate,
    HiveListItem,
    HiveOut,
    HiveUpdate,
    ReplaceFamilyRequest,
)
from app.schemas.queen import AssignQueenRequest, RemoveQueenRequest
from app.services import audit_service as audit
from app.services import queen_service
from app.services.apiary_service import get_apiary
from app.services.queen_service import LIVING_HIVE_STATUSES
from app.utils.errors import ConflictError, NotFoundError, ValidationFailed

# What happens to the family and queen when a hive leaves the apiary
_ARCHIVE_EFFECTS = {
    HiveStatus.SOLD: (FamilyStatus.SOLD, QueenStatus.SOLD),
    HiveStatus.LOST: (FamilyStatus.DEAD, QueenStatus.DEAD),
}

# What happens to the queen when the family ends without a replacement
_FAMILY_END_QUEEN = {
    FamilyStatus.SOLD: QueenStatus.SOLD,
    FamilyStatus.DEAD: QueenStatus.DEAD,
    FamilyStatus.ABSCONDED: QueenStatus.LOST,
    FamilyStatus.MERGED: QueenStatus.REPLACED,
    FamilyStatus.REPLACED: QueenStatus.REPLACED,
}


# ---------- reading ----------

def get_hive(db: Session, hive_id: uuid.UUID) -> Hive:
    hive = db.get(Hive, hive_id)
    if hive is None:
        raise NotFoundError("Улей не найден")
    return hive


def to_out(hive: Hive) -> HiveOut:
    return HiveOut(
        id=hive.id,
        apiary=ApiaryBrief.model_validate(hive.apiary),
        hive_number=hive.hive_number,
        hive_type=hive.hive_type,
        status=hive.status,
        is_archived=hive.status in ARCHIVED_HIVE_STATUSES,
        installation_date=hive.installation_date,
        colonization_date=hive.colonization_date,
        last_inspection_at=hive.last_inspection_at,
        next_inspection_at=hive.next_inspection_at,
        notes=hive.notes,
        version=hive.version,
        current_family=FamilyOut.model_validate(hive.current_family) if hive.current_family else None,
        current_queen=queen_service.to_brief(hive.current_queen),
        created_at=hive.created_at,
        updated_at=hive.updated_at,
    )


def to_list_item(hive: Hive) -> HiveListItem:
    queen = queen_service.to_brief(hive.current_queen)
    return HiveListItem(
        id=hive.id,
        apiary=ApiaryBrief.model_validate(hive.apiary),
        hive_number=hive.hive_number,
        hive_type=hive.hive_type,
        status=hive.status,
        is_archived=hive.status in ARCHIVED_HIVE_STATUSES,
        strength=hive.current_family.strength if hive.current_family else None,
        queen_id=queen.id if queen else None,
        queen_code=queen.queen_code if queen else None,
        queen_age_label=queen.age_label if queen else None,
        last_inspection_at=hive.last_inspection_at,
        next_inspection_at=hive.next_inspection_at,
    )


def history(db: Session, hive: Hive) -> list[AuditEntryOut]:
    return [
        AuditEntryOut(
            id=e.id, created_at=e.created_at, user_name=e.user.display_name if e.user else None,
            entity_type=e.entity_type, entity_id=e.entity_id, action=e.action,
            old_value=e.old_value, new_value=e.new_value, comment=e.comment,
        )
        for e in repo.hive_history(db, hive.id)
    ]


# ---------- helpers ----------

def _ensure_number_free(db: Session, apiary_id: uuid.UUID, number: str, exclude: uuid.UUID | None = None):
    clash = repo.find_active_hive_by_number(db, apiary_id, number, exclude)
    if clash:
        raise ConflictError(f"Улей №{number} уже есть на пасеке «{clash.apiary.name}»")


def _ensure_not_archived(hive: Hive) -> None:
    if hive.status in ARCHIVED_HIVE_STATUSES:
        raise ConflictError(f"Улей №{hive.hive_number} в архиве, его нельзя изменять")


def _new_family(db: Session, hive: Hive, data: FamilyCreate, start: date) -> BeeFamily:
    family = BeeFamily(
        hive_id=hive.id, strength=data.strength, origin=data.origin, start_date=start,
        status=FamilyStatus.ACTIVE, notes=data.notes,
    )
    db.add(family)
    db.flush()
    hive.current_family_id = family.id
    return family


def _end_family(db: Session, family: BeeFamily, status: FamilyStatus, when: date, reason: str | None) -> None:
    if when < family.start_date:
        raise ValidationFailed("Дата окончания раньше даты заселения семьи")
    family.status = status
    family.end_date = when
    family.end_reason = reason
    db.flush()  # free the "one active family per hive" slot


# ---------- hives ----------

def create_hive(db: Session, data: HiveCreate, user: User, *, commit: bool = True) -> Hive:
    apiary = get_apiary(db, data.apiary_id)
    if apiary.is_archived:
        raise ConflictError("Пасека в архиве — в неё нельзя добавить улей")
    _ensure_number_free(db, apiary.id, data.hive_number)

    status = data.status or (HiveStatus.ACTIVE if data.family else HiveStatus.EMPTY)
    if status != HiveStatus.EMPTY and not data.family:
        raise ValidationFailed("Для заселённого улья укажите пчелиную семью или выберите статус «Пустой»")

    hive = Hive(
        apiary_id=apiary.id, hive_number=data.hive_number, hive_type=data.hive_type, status=status,
        installation_date=data.installation_date or today(), colonization_date=data.colonization_date,
        next_inspection_at=data.next_inspection_at, notes=data.notes, version=1,
    )
    db.add(hive)
    db.flush()

    if data.family:
        start = data.family.start_date or data.colonization_date or today()
        _new_family(db, hive, data.family, start)
        hive.colonization_date = hive.colonization_date or start

    audit.record(db, user=user, entity_type="hive", entity_id=hive.id, hive_id=hive.id, action="created",
                 new=audit.snapshot(hive))

    if data.queen_id:
        if hive.status == HiveStatus.QUEENLESS:
            raise ValidationFailed("Улей отмечен «Без матки», но выбрана матка")
        queen_service.assign_queen(db, hive, AssignQueenRequest(queen_id=data.queen_id), user, commit=False)

    if commit:
        db.commit()
        db.refresh(hive)
    else:
        db.flush()
    return hive


def update_hive(db: Session, hive: Hive, data: HiveUpdate, user: User) -> Hive:
    if data.version is not None and data.version != hive.version:
        raise ConflictError("Улей уже изменил другой пользователь. Обновите карточку и повторите.")

    changes = data.model_dump(exclude_unset=True, exclude={"version", "comment"})
    if hive.status in ARCHIVED_HIVE_STATUSES and set(changes) - {"notes"}:
        _ensure_not_archived(hive)

    if "hive_number" in changes and changes["hive_number"] != hive.hive_number:
        _ensure_number_free(db, hive.apiary_id, changes["hive_number"], exclude=hive.id)

    new_status = changes.get("status")
    if new_status and new_status != hive.status:
        _validate_status_change(hive, new_status)

    before = audit.snapshot(hive)
    for key, value in changes.items():
        if key != "status":
            setattr(hive, key, value)

    if new_status and new_status != hive.status:
        if new_status in _ARCHIVE_EFFECTS:
            _archive(db, hive, new_status, user, data.comment)
        hive.status = new_status

    old, new = audit.diff(before, audit.snapshot(hive))
    if new:
        hive.version += 1
        action = "number_changed" if set(new) == {"hive_number"} else "updated"
        audit.record(db, user=user, entity_type="hive", entity_id=hive.id, hive_id=hive.id,
                     action=action, old=old, new=new, comment=data.comment)
    db.commit()
    db.refresh(hive)
    return hive


def _validate_status_change(hive: Hive, status: HiveStatus) -> None:
    if status == HiveStatus.EMPTY and hive.current_family_id:
        raise ConflictError("В улье есть семья. Сначала завершите семью (продана, погибла, слетела…).")
    if status in LIVING_HIVE_STATUSES and not hive.current_family_id:
        raise ConflictError("В улье нет семьи. Сначала заселите пчелиную семью.")
    if status == HiveStatus.QUEENLESS and hive.current_queen_id:
        raise ConflictError("В улье записана матка. Сначала уберите её через «Убрать матку».")


def _archive(db: Session, hive: Hive, status: HiveStatus, user: User, comment: str | None) -> None:
    family_status, queen_status = _ARCHIVE_EFFECTS[status]
    when = today()
    reason = comment or ("Улей продан" if status == HiveStatus.SOLD else "Улей потерян")
    if hive.current_queen:
        code = hive.current_queen.queen_code
        queen_service._detach(db, hive.current_queen, hive, status=queen_status, when=when, reason=reason)
        audit.record(db, user=user, entity_type="hive", entity_id=hive.id, hive_id=hive.id,
                     action="queen_removed", old={"queen_code": code},
                     new={"queen_code": None, "queen_status": queen_status.value}, comment=reason)
    if hive.current_family:
        _end_family(db, hive.current_family, family_status, when, reason)
        hive.current_family_id = None


# ---------- families ----------

def replace_family(db: Session, hive: Hive, data: ReplaceFamilyRequest, user: User, *, commit: bool = True) -> Hive:
    """Settle a new family. If one lives there, it ends with `previous_status`."""
    _ensure_not_archived(hive)
    start = data.start_date or today()
    previous = hive.current_family
    old_value = None
    if previous:
        if hive.current_queen:
            code = hive.current_queen.queen_code
            queen_service._detach(db, hive.current_queen, hive, status=QueenStatus.REPLACED, when=start,
                                  reason="Смена семьи")
            audit.record(db, user=user, entity_type="hive", entity_id=hive.id, hive_id=hive.id,
                         action="queen_removed", old={"queen_code": code}, new={"queen_code": None},
                         comment="Смена семьи")
        _end_family(db, previous, data.previous_status, start, data.end_reason)
        old_value = {"family_id": str(previous.id), "strength": previous.strength.value,
                     "family_status": data.previous_status.value}

    family = _new_family(db, hive, data, start)
    hive.colonization_date = start
    if hive.status in (HiveStatus.EMPTY, HiveStatus.QUEENLESS):
        hive.status = HiveStatus.ACTIVE
    hive.version += 1
    audit.record(db, user=user, entity_type="hive", entity_id=hive.id, hive_id=hive.id,
                 action="family_replaced" if previous else "family_settled", old=old_value,
                 new={"family_id": str(family.id), "strength": family.strength.value,
                      "origin": family.origin.value, "start_date": start.isoformat()},
                 comment=data.comment)
    if commit:
        db.commit()
        db.refresh(hive)
    else:
        db.flush()
    return hive


def end_family(db: Session, hive: Hive, data: EndFamilyRequest, user: User, *, commit: bool = True) -> Hive:
    _ensure_not_archived(hive)
    family = hive.current_family
    if family is None:
        raise ConflictError("В улье нет семьи")
    when = data.end_date or today()
    if hive.current_queen:
        code = hive.current_queen.queen_code
        q_status = _FAMILY_END_QUEEN[data.status]
        queen_service._detach(db, hive.current_queen, hive, status=q_status, when=when, reason=data.end_reason)
        audit.record(db, user=user, entity_type="hive", entity_id=hive.id, hive_id=hive.id,
                     action="queen_removed", old={"queen_code": code},
                     new={"queen_code": None, "queen_status": q_status.value}, comment=data.end_reason)
    old_status = hive.status
    _end_family(db, family, data.status, when, data.end_reason)
    hive.current_family_id = None
    hive.status = HiveStatus.EMPTY
    hive.version += 1
    audit.record(db, user=user, entity_type="hive", entity_id=hive.id, hive_id=hive.id, action="family_ended",
                 old={"family_id": str(family.id), "status": old_status.value},
                 new={"family_status": data.status.value, "status": HiveStatus.EMPTY.value},
                 comment=data.end_reason)
    if commit:
        db.commit()
        db.refresh(hive)
    else:
        db.flush()
    return hive


def update_family(db: Session, hive: Hive, data: FamilyUpdate, user: User) -> Hive:
    _ensure_not_archived(hive)
    family = hive.current_family
    if family is None:
        raise ConflictError("В улье нет семьи")
    before = audit.snapshot(family, ["strength", "notes"])
    for key, value in data.model_dump(exclude_unset=True, exclude={"comment"}).items():
        setattr(family, key, value)
    old, new = audit.diff(before, audit.snapshot(family, ["strength", "notes"]))
    if new:
        hive.version += 1
        audit.record(db, user=user, entity_type="bee_family", entity_id=family.id, hive_id=hive.id,
                     action="updated", old=old, new=new, comment=data.comment)
    db.commit()
    db.refresh(hive)
    return hive


def remove_queen(db: Session, hive: Hive, data: RemoveQueenRequest, user: User) -> Hive:
    _ensure_not_archived(hive)
    return queen_service.remove_queen(db, hive, data, user)
