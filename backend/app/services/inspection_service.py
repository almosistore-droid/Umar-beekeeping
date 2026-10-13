"""Hive inspections (stage 3, user story 1).

After every create/correction the hive's derived state is recomputed from the
latest inspection: last/next inspection dates and the current family strength.
"""
import uuid
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Hive, Inspection, User
from app.models.enums import InspectionHealth
from app.schemas.health import InspectionCreate, InspectionUpdate
from app.services import audit_service as audit
from app.schemas.common import local_date
from app.services.health_service import get_hive_for_record
from app.utils.errors import NotFoundError

DEFAULT_INTERVAL_DAYS = 7
# Dates are stored as noon UTC so they show as the same calendar day in any time zone (±11 h)
_NOON = time(12, 0, tzinfo=timezone.utc)

_FIELDS = ["inspected_at", "strength", "frames_total", "brood_frames", "honey_frames", "pollen_frames",
           "queen_present", "queen_condition", "egg_laying", "queen_cells", "swarming_signs", "food_level",
           "aggressiveness", "health_status", "next_inspection_at", "notes"]


def _latest(db: Session, hive_id: uuid.UUID) -> Inspection | None:
    return db.scalars(select(Inspection).where(Inspection.hive_id == hive_id)
                      .order_by(Inspection.inspected_at.desc(), Inspection.created_at.desc()).limit(1)).first()


def _recompute_hive(db: Session, hive: Hive, user: User) -> None:
    db.flush()
    latest = _latest(db, hive.id)
    if latest is None:
        hive.last_inspection_at = hive.next_inspection_at = None
        return
    next_day = latest.next_inspection_at or (local_date(latest.inspected_at) + timedelta(days=DEFAULT_INTERVAL_DAYS))
    new_last, new_next = latest.inspected_at, datetime.combine(next_day, _NOON)
    if (hive.last_inspection_at, hive.next_inspection_at) != (new_last, new_next):
        hive.last_inspection_at, hive.next_inspection_at = new_last, new_next
        hive.version += 1

    family = hive.current_family
    if family and family.strength != latest.strength:
        old = family.strength
        family.strength = latest.strength
        audit.record(db, user=user, entity_type="bee_family", entity_id=family.id, hive_id=hive.id,
                     action="updated", old={"strength": old.value}, new={"strength": latest.strength.value},
                     comment="По результатам осмотра")


def warnings_for(inspection: Inspection, hive: Hive) -> list[dict[str, str]]:
    """Hints shown after saving. Nothing is changed automatically (FR-005)."""
    out = []
    if inspection.queen_present is False and inspection.egg_laying is False:
        out.append({"code": "possible_queenless",
                    "message": "Матка не найдена и яиц нет — возможно, семья осталась без матки."
                               + (" В карточке записана матка — проверьте её." if hive.current_queen_id else
                                  " Отметьте улей «Без матки» или подсадите матку.")})
    if inspection.swarming_signs or inspection.queen_cells >= 3:
        out.append({"code": "swarming_risk",
                    "message": "Есть признаки роения — примите противороевые меры."})
    if inspection.health_status == InspectionHealth.SICK:
        out.append({"code": "health_issue", "message": "Отмечено, что семья болеет — запишите болезнь."})
    return out


def create_inspection(db: Session, hive_id: uuid.UUID, data: InspectionCreate, user: User):
    hive = get_hive_for_record(db, hive_id)
    values = data.model_dump()
    values["inspected_at"] = values["inspected_at"] or datetime.now(timezone.utc)
    inspection = Inspection(hive_id=hive.id, user_id=user.id, **values)
    db.add(inspection)
    _recompute_hive(db, hive, user)
    db.commit()
    db.refresh(inspection)
    db.refresh(hive)
    return inspection, hive, warnings_for(inspection, hive)


def update_inspection(db: Session, inspection_id: uuid.UUID, data: InspectionUpdate, user: User):
    inspection = db.get(Inspection, inspection_id)
    if inspection is None:
        raise NotFoundError("Осмотр не найден")
    hive = get_hive_for_record(db, inspection.hive_id, require_family=False)
    before = audit.snapshot(inspection, _FIELDS)
    values = data.model_dump(exclude={"comment"})
    values["inspected_at"] = values["inspected_at"] or inspection.inspected_at
    for k in _FIELDS:
        setattr(inspection, k, values[k])
    old, new = audit.diff(before, audit.snapshot(inspection, _FIELDS))
    if new:
        audit.record(db, user=user, entity_type="inspection", entity_id=inspection.id, hive_id=hive.id,
                     action="corrected", old=old, new=new, comment=data.comment)
        _recompute_hive(db, hive, user)
    db.commit()
    db.refresh(inspection)
    db.refresh(hive)
    return inspection, hive, warnings_for(inspection, hive)


def list_inspections(db: Session, hive_id: uuid.UUID, limit: int = 200) -> list[Inspection]:
    return list(db.scalars(select(Inspection).where(Inspection.hive_id == hive_id)
                           .order_by(Inspection.inspected_at.desc()).limit(limit)).unique())
