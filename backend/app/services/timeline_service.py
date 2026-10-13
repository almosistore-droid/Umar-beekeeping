"""One chronological timeline per hive (stage 3, user story 5).

Merges stage-3 records with stage-2 history events from audit_logs. Audit entries
that only duplicate a record (a case being opened/resolved) are skipped.
"""
import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import AuditLog, Feeding, HiveDisease, Inspection, Treatment
from app.models.enums import DiseaseCaseStatus
from app.schemas.health import TimelineItem
from app.utils import labels as L

_NOON = time(12, 0, tzinfo=timezone.utc)
_SKIP_ACTIONS = {"disease_opened", "disease_resolved", "task_done"}


def _at(d: date) -> datetime:
    return datetime.combine(d, _NOON)


def _qty(q: Decimal) -> str:
    return f"{q.normalize():f}".rstrip(".") if q == q.to_integral() else f"{q:f}".rstrip("0").rstrip(".")


def _inspection(i: Inspection) -> TimelineItem:
    details = [f"Сила: {L.STRENGTH[i.strength]}"]
    if i.frames_total:
        parts = [f"расплод {i.brood_frames}", f"мёд {i.honey_frames}", f"перга {i.pollen_frames}"]
        details.append(f"Рамки: {i.frames_total} ({', '.join(parts)})")
    if i.queen_present is not None:
        details.append("Матка: видна" if i.queen_present else "Матка: не найдена")
    if i.egg_laying is False:
        details.append("Яиц нет")
    if i.queen_cells:
        details.append(f"Маточников: {i.queen_cells}")
    if i.swarming_signs:
        details.append("Признаки роения")
    if i.food_level:
        details.append(f"Корм: {L.FOOD_LEVEL[i.food_level]}")
    if i.health_status.value != "HEALTHY":
        details.append(f"Здоровье: {L.HEALTH[i.health_status]}")
    if i.notes:
        details.append(i.notes)
    return TimelineItem(kind="inspection", at=i.inspected_at, title="Осмотр", details=details,
                        author=i.user.display_name if i.user else None, ref_id=i.id)


def _case_items(c: HiveDisease) -> list[TimelineItem]:
    author = c.author.display_name if c.author else None
    opened = [f"Тяжесть: {L.SEVERITY[c.severity]}"]
    if c.symptoms:
        opened.append(c.symptoms)
    items = [TimelineItem(kind="disease_opened", at=_at(c.detected_at), title=f"Обнаружена болезнь: {c.disease.name}",
                          details=opened, author=author, ref_id=c.id)]
    if c.status == DiseaseCaseStatus.RESOLVED and c.resolved_at:
        items.append(TimelineItem(kind="disease_resolved", at=_at(c.resolved_at),
                                  title=f"Вылечено: {c.disease.name}", details=[], author=author, ref_id=c.id))
    return items


def _treatment(t: Treatment) -> TimelineItem:
    title = f"Обработка: {t.disease.name}" if t.disease else "Обработка"
    details = [" ".join(x for x in (t.medication, t.dosage) if x)]
    if t.method:
        details.append(t.method)
    if t.result:
        details.append(f"Результат: {t.result}")
    if t.next_treatment_date:
        details.append(f"Следующая: {t.next_treatment_date.strftime('%d.%m.%Y')}")
    return TimelineItem(kind="treatment", at=_at(t.treated_at), title=title, details=details,
                        author=t.performer.display_name if t.performer else None, ref_id=t.id)


def _feeding(f: Feeding) -> TimelineItem:
    details = [f"{L.FEED_TYPE[f.feed_type]}, {_qty(f.quantity)} {L.FEED_UNIT[f.unit]}"]
    if f.reason:
        details.append(f.reason)
    if f.next_feeding_date:
        details.append(f"Следующая: {f.next_feeding_date.strftime('%d.%m.%Y')}")
    return TimelineItem(kind="feeding", at=_at(f.fed_at), title="Подкормка", details=details,
                        author=f.author.display_name if f.author else None, ref_id=f.id)


def _event(e: AuditLog) -> TimelineItem:
    return TimelineItem(kind="event", at=e.created_at, title=e.action, details=[],
                        author=e.user.display_name if e.user else None, ref_id=e.entity_id,
                        action=e.action, entity_type=e.entity_type, old_value=e.old_value,
                        new_value=e.new_value, comment=e.comment)


def hive_timeline(db: Session, hive_id: uuid.UUID, limit: int = 300) -> list[TimelineItem]:
    items: list[TimelineItem] = []
    items += [_inspection(i) for i in db.scalars(select(Inspection).where(Inspection.hive_id == hive_id)).unique()]
    for c in db.scalars(select(HiveDisease).where(HiveDisease.hive_id == hive_id)).unique():
        items += _case_items(c)
    items += [_treatment(t) for t in db.scalars(select(Treatment).where(Treatment.hive_id == hive_id)).unique()]
    items += [_feeding(f) for f in db.scalars(select(Feeding).where(Feeding.hive_id == hive_id)).unique()]
    events = db.scalars(select(AuditLog).where(or_(AuditLog.hive_id == hive_id, AuditLog.entity_id == hive_id))
                        .order_by(AuditLog.created_at.desc()).limit(limit)).unique()
    for e in events:
        if e.action in _SKIP_ACTIONS:
            continue
        if e.entity_type == "bee_family" and e.comment == "По результатам осмотра":
            continue  # already visible as the inspection's strength
        items.append(_event(e))
    items.sort(key=lambda x: x.at, reverse=True)
    return items[:limit]
