"""Colony operations (stage 4): movement, swarm, split, merge, wintering.

Every operation runs in one transaction and reuses the stage 2 primitives for hives,
families and queens, so their history and audit rules apply unchanged.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ARCHIVED_HIVE_STATUSES,
    REMOVED_QUEEN_STATUSES,
    Apiary,
    FamilyOrigin,
    FamilyStatus,
    Hive,
    HiveMerge,
    HiveMovement,
    HiveSplit,
    HiveStatus,
    Queen,
    QueenStatus,
    Swarm,
    User,
    Wintering,
)
from app.models.enums import WinteringResult
from app.repositories import hive_repository as repo
from app.schemas.common import today
from app.schemas.hive import EndFamilyRequest, FamilyCreate, HiveCreate, ReplaceFamilyRequest
from app.schemas.operations import MergeCreate, MoveRequest, SplitCreate, SwarmCreate, WinteringFinish, WinteringStart
from app.schemas.queen import AssignQueenRequest
from app.services import audit_service as audit
from app.services import hive_service, queen_service
from app.services.health_service import get_hive_for_record
from app.utils.errors import ConflictError, NotFoundError, ValidationFailed


def _apiary(db: Session, apiary_id: uuid.UUID) -> Apiary:
    apiary = db.get(Apiary, apiary_id)
    if apiary is None:
        raise NotFoundError("Пасека не найдена")
    if apiary.is_archived:
        raise ConflictError(f"Пасека «{apiary.name}» в архиве")
    return apiary


def _empty_hive(db: Session, hive_id: uuid.UUID) -> Hive:
    hive = db.get(Hive, hive_id)
    if hive is None:
        raise NotFoundError("Улей не найден")
    if hive.status in ARCHIVED_HIVE_STATUSES:
        raise ConflictError(f"Улей №{hive.hive_number} в архиве")
    if hive.current_family_id is not None:
        raise ConflictError(f"В улье №{hive.hive_number} уже живёт семья — выберите пустой улей")
    return hive


def _free_queen(db: Session, queen_id: uuid.UUID) -> Queen:
    queen = db.get(Queen, queen_id)
    if queen is None:
        raise NotFoundError("Матка не найдена")
    if queen.status in REMOVED_QUEEN_STATUSES:
        raise ConflictError(f"Матка {queen.queen_code} выбыла")
    if queen.current_hive_id:
        raise ConflictError(f"Матка {queen.queen_code} уже в улье — выберите свободную")
    return queen


def _new_or_empty_hive(db: Session, *, apiary_id: uuid.UUID, number: str | None, existing_id: uuid.UUID | None,
                       like: Hive, origin: FamilyOrigin, strength, start, user: User, comment: str) -> Hive:
    """Settle a new family either into an existing empty hive or a newly created one."""
    if existing_id:
        hive = _empty_hive(db, existing_id)
        hive_service.replace_family(db, hive, ReplaceFamilyRequest(strength=strength, origin=origin, start_date=start,
                                                                   comment=comment), user, commit=False)
        return hive
    return hive_service.create_hive(db, HiveCreate(
        apiary_id=apiary_id, hive_number=number, hive_type=like.hive_type, installation_date=start,
        family=FamilyCreate(strength=strength, origin=origin, start_date=start), notes=comment), user, commit=False)


def _finish(db: Session, *hives: Hive) -> None:
    db.commit()
    for h in hives:
        db.refresh(h)


# ---------- movement ----------

def move_hive(db: Session, hive_id: uuid.UUID, data: MoveRequest, user: User) -> Hive:
    hive = get_hive_for_record(db, hive_id, require_family=False)
    target = _apiary(db, data.to_apiary_id)
    if target.id == hive.apiary_id:
        raise ValidationFailed("Улей уже на этой пасеке")
    number = data.new_hive_number or hive.hive_number
    clash = repo.find_active_hive_by_number(db, target.id, number, exclude_id=hive.id)
    if clash:
        raise ConflictError(f"На пасеке «{target.name}» уже есть улей №{number}. Укажите новый номер для этого улья.")
    when = data.movement_date or today()
    source_name = hive.apiary.name
    db.add(HiveMovement(hive_id=hive.id, from_apiary_id=hive.apiary_id, to_apiary_id=target.id, movement_date=when,
                        reason=data.reason, notes=data.notes, performed_by=user.id))
    old = {"apiary": source_name, "hive_number": hive.hive_number}
    hive.apiary_id = target.id
    hive.hive_number = number
    hive.version += 1
    audit.record(db, user=user, entity_type="hive", entity_id=hive.id, hive_id=hive.id, action="moved",
                 old=old, new={"apiary": target.name, "hive_number": number}, comment=data.reason)
    db.commit()
    db.expire(hive, ["apiary"])
    db.refresh(hive)
    return hive


def list_movements(db: Session, hive_id: uuid.UUID) -> list[HiveMovement]:
    return list(db.scalars(select(HiveMovement).where(HiveMovement.hive_id == hive_id)
                           .order_by(HiveMovement.movement_date.desc(), HiveMovement.created_at.desc())).unique())


# ---------- swarm ----------

def record_swarm(db: Session, hive_id: uuid.UUID, data: SwarmCreate, user: User) -> tuple[Swarm, Hive | None]:
    hive = get_hive_for_record(db, hive_id)
    when = data.swarm_date or today()
    queen = _free_queen(db, data.queen_id) if data.queen_id else None
    new_hive = None
    if data.captured and (data.settle_into_hive_id or data.new_hive_number):
        if data.settle_into_hive_id == hive.id:
            raise ValidationFailed("Рой нельзя посадить в тот же улей")
        new_hive = _new_or_empty_hive(db, apiary_id=hive.apiary_id, number=data.new_hive_number,
                                      existing_id=data.settle_into_hive_id, like=hive, origin=FamilyOrigin.SWARM,
                                      strength="MEDIUM", start=when, user=user,
                                      comment=f"Рой из улья №{hive.hive_number}")
        if queen:
            queen_service.assign_queen(db, new_hive, AssignQueenRequest(queen_id=queen.id, installed_at=when), user,
                                       commit=False)
    swarm = Swarm(hive_id=hive.id, swarm_date=when, swarm_count=data.swarm_count, captured=data.captured,
                  new_hive_id=new_hive.id if new_hive else None, new_queen_id=queen.id if queen else None,
                  actions=data.actions, notes=data.notes, created_by=user.id)
    db.add(swarm)
    db.flush()
    audit.record(db, user=user, entity_type="swarm", entity_id=swarm.id, hive_id=hive.id, action="swarmed",
                 new={"swarm_count": data.swarm_count, "captured": data.captured,
                      "new_hive_number": new_hive.hive_number if new_hive else None})
    if new_hive:
        audit.record(db, user=user, entity_type="swarm", entity_id=swarm.id, hive_id=new_hive.id,
                     action="swarm_settled", new={"from_hive_number": hive.hive_number})
    _finish(db, *(h for h in (hive, new_hive) if h))
    return swarm, new_hive


# ---------- split ----------

def split_hive(db: Session, hive_id: uuid.UUID, data: SplitCreate, user: User) -> tuple[Hive, Hive]:
    source = get_hive_for_record(db, hive_id)
    when = data.split_date or today()
    queen = _free_queen(db, data.queen_id) if data.queen_id else None
    if data.target_hive_id == source.id:
        raise ValidationFailed("Нельзя разделить улей сам в себя")
    new_hive = _new_or_empty_hive(db, apiary_id=source.apiary_id, number=data.new_hive_number,
                                  existing_id=data.target_hive_id, like=source, origin=FamilyOrigin.SPLIT,
                                  strength=data.strength, start=when, user=user,
                                  comment=f"Отводок от улья №{source.hive_number}")
    if queen:
        queen_service.assign_queen(db, new_hive, AssignQueenRequest(queen_id=queen.id, installed_at=when), user,
                                   commit=False)
    elif new_hive.current_queen_id is None:
        new_hive.status = HiveStatus.QUEENLESS
    split = HiveSplit(source_hive_id=source.id, new_hive_id=new_hive.id, split_date=when,
                      queen_id=queen.id if queen else None, notes=data.notes, created_by=user.id)
    db.add(split)
    db.flush()
    audit.record(db, user=user, entity_type="hive_split", entity_id=split.id, hive_id=source.id, action="split",
                 new={"new_hive_number": new_hive.hive_number}, comment=data.notes)
    audit.record(db, user=user, entity_type="hive_split", entity_id=split.id, hive_id=new_hive.id,
                 action="split_created", new={"source_hive_number": source.hive_number,
                                              "queen_code": queen.queen_code if queen else None})
    _finish(db, source, new_hive)
    return source, new_hive


# ---------- merge ----------

def merge_hives(db: Session, data: MergeCreate, user: User) -> Hive:
    sources = [get_hive_for_record(db, hid) for hid in data.source_hive_ids]
    when = data.merge_date or today()
    # The queen to keep must live in one of the merged hives
    queens_in_sources = {h.current_queen_id for h in sources if h.current_queen_id}
    if data.keep_queen_id and data.keep_queen_id not in queens_in_sources:
        raise ValidationFailed("Сохранить можно только матку одного из объединяемых ульев")

    if data.target_hive_id:
        target = next((h for h in sources if h.id == data.target_hive_id), None)
        if target is None:
            target = _empty_hive(db, data.target_hive_id)
    else:
        apiary_id = sources[0].apiary_id
        target = hive_service.create_hive(db, HiveCreate(
            apiary_id=apiary_id, hive_number=data.new_hive_number, hive_type=sources[0].hive_type,
            installation_date=when, family=FamilyCreate(strength=_merged_strength(sources), origin=FamilyOrigin.MERGE,
                                                         start_date=when),
            notes="Создан объединением"), user, commit=False)
    if target.current_family_id is None:  # existing empty hive chosen as target
        hive_service.replace_family(db, target, ReplaceFamilyRequest(
            strength=_merged_strength(sources), origin=FamilyOrigin.MERGE, start_date=when,
            comment="Объединение"), user, commit=False)

    merged_away = [h for h in sources if h.id != target.id]
    source_numbers = [h.hive_number for h in merged_away]
    kept = db.get(Queen, data.keep_queen_id) if data.keep_queen_id else None

    for hive in merged_away:
        if hive.current_queen and (kept is None or hive.current_queen_id != kept.id):
            queen_service._detach(db, hive.current_queen, hive, status=QueenStatus.REPLACED, when=when,
                                  reason=f"Объединение в улей №{target.hive_number}")
        elif kept is not None and hive.current_queen_id == kept.id:
            queen_service._detach(db, kept, hive, status=kept.status, when=when,
                                  reason=f"Перенесена при объединении в улей №{target.hive_number}")
        hive_service._end_family(db, hive.current_family, FamilyStatus.MERGED, when,
                                 f"Объединена в улей №{target.hive_number}")
        hive.current_family_id = None
        old_status = hive.status
        hive.status = HiveStatus.MERGED
        hive.version += 1
        audit.record(db, user=user, entity_type="hive", entity_id=hive.id, hive_id=hive.id, action="merged_into",
                     old={"status": old_status.value}, new={"status": "MERGED", "target_hive_number": target.hive_number})

    if kept is not None and target.current_queen_id != kept.id:
        if target.current_queen:
            queen_service._detach(db, target.current_queen, target, status=QueenStatus.REPLACED, when=when,
                                  reason="Объединение семей")
        queen_service.assign_queen(db, target, AssignQueenRequest(queen_id=kept.id, installed_at=when,
                                                                  comment="Объединение семей"), user, commit=False)

    if target.current_queen_id is None:
        target.status = HiveStatus.QUEENLESS

    merge = HiveMerge(target_hive_id=target.id, merge_date=when, kept_queen_id=kept.id if kept else None,
                      notes=data.notes, created_by=user.id)
    merge.sources = merged_away
    db.add(merge)
    db.flush()
    audit.record(db, user=user, entity_type="hive_merge", entity_id=merge.id, hive_id=target.id, action="merge_target",
                 new={"source_hive_numbers": source_numbers, "queen_code": kept.queen_code if kept else None},
                 comment=data.notes)
    _finish(db, target, *merged_away)
    return target


def _merged_strength(hives: list[Hive]):
    from app.models import FamilyStrength
    order = list(FamilyStrength)
    levels = [order.index(h.current_family.strength) for h in hives if h.current_family]
    return order[min(len(order) - 1, max(levels) + 1)] if levels else FamilyStrength.MEDIUM


# ---------- wintering ----------

def start_wintering(db: Session, hive_id: uuid.UUID, data: WinteringStart, user: User) -> Wintering:
    hive = get_hive_for_record(db, hive_id)
    if db.scalar(select(Wintering.id).where(Wintering.hive_id == hive.id, Wintering.season == data.season)):
        raise ConflictError(f"Зимовка {data.season} для улья №{hive.hive_number} уже записана")
    w = Wintering(hive_id=hive.id, start_date=data.start_date or today(), created_by=user.id,
                  **data.model_dump(exclude={"start_date"}))
    db.add(w)
    db.flush()
    audit.record(db, user=user, entity_type="wintering", entity_id=w.id, hive_id=hive.id, action="wintering_started",
                 new={"season": w.season})
    db.commit()
    db.refresh(w)
    return w


def finish_wintering(db: Session, wintering_id: uuid.UUID, data: WinteringFinish, user: User) -> tuple[Wintering, Hive]:
    w = db.get(Wintering, wintering_id)
    if w is None:
        raise NotFoundError("Зимовка не найдена")
    if w.end_date is not None:
        raise ConflictError("Зимовка уже завершена")
    end = data.end_date or today()
    if end < w.start_date:
        raise ValidationFailed("Дата окончания зимовки раньше даты начала")
    hive = db.get(Hive, w.hive_id)
    w.end_date, w.spring_strength, w.result = end, data.spring_strength, data.result
    if data.notes:
        w.notes = f"{w.notes}\n{data.notes}" if w.notes else data.notes
    audit.record(db, user=user, entity_type="wintering", entity_id=w.id, hive_id=hive.id, action="wintering_finished",
                 new={"season": w.season, "result": data.result.value})
    if data.result == WinteringResult.DIED and hive.current_family_id:
        hive_service.end_family(db, hive, EndFamilyRequest(status=FamilyStatus.DEAD, end_date=end,
                                                           end_reason=f"Погибла на зимовке {w.season}"),
                                user, commit=False)
    elif data.spring_strength and hive.current_family:
        hive.current_family.strength = data.spring_strength
    db.commit()
    db.refresh(w)
    db.refresh(hive)
    return w, hive


def list_winterings(db: Session, hive_id: uuid.UUID) -> list[Wintering]:
    return list(db.scalars(select(Wintering).where(Wintering.hive_id == hive_id)
                           .order_by(Wintering.start_date.desc())).unique())
