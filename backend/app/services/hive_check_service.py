"""«Проверка улья»: a read-only summary of a hive's state with the issues that need attention.

Nothing is written. The rules mirror what a beekeeper looks at when walking up to a hive:
family and queen, the last inspection, overdue inspection, diseases, reminders.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ARCHIVED_HIVE_STATUSES, Hive, HiveStatus, User
from app.models.enums import (
    ACTIVE_CASE_STATUSES,
    DiseaseCaseStatus,
    FamilyStrength,
    FoodLevel,
    InspectionHealth,
    TaskStatus,
)
from app.models.health import HiveDisease, Inspection
from app.schemas.apiary import ApiaryBrief
from app.schemas.check import CheckCase, CheckInspection, CheckIssue, CheckQueen, CheckTask, HiveCheckOut
from app.services import health_service, honey_service, queen_service
from app.schemas.common import today as utc_today
from app.utils.age import plural_ru
from app.utils.labels import CASE_STATUS

_HEADLINES = {"ok": "Всё в порядке", "attention": "Требует внимания", "problem": "Есть проблемы"}
_WEAK = {FamilyStrength.WEAK, FamilyStrength.VERY_WEAK}


def _days(n: int) -> str:
    return f"{n} {plural_ru(n, 'день', 'дня', 'дней')}"


def check(db: Session, hive: Hive, _: User) -> HiveCheckOut:
    today = utc_today()
    issues: list[CheckIssue] = []

    def add(code: str, level: str, message: str) -> None:
        issues.append(CheckIssue(code=code, level=level, message=message))

    archived = hive.status in ARCHIVED_HIVE_STATUSES
    family = hive.current_family
    queen = queen_service.to_brief(hive.current_queen)

    latest = db.scalars(select(Inspection).where(Inspection.hive_id == hive.id)
                        .order_by(Inspection.inspected_at.desc(), Inspection.created_at.desc()).limit(1)).first()
    cases = [c for c in db.scalars(select(HiveDisease).where(HiveDisease.hive_id == hive.id)).unique()
             if c.status != DiseaseCaseStatus.RESOLVED]
    tasks = [t for t, _num in health_service.list_tasks(db, status=TaskStatus.OPEN, hive_id=hive.id, due_before=None)]

    if archived:
        add("archived", "problem", "Улей в архиве — он больше не на пасеке")
    elif not family:
        add("no_family", "attention", "В улье нет пчелиной семьи")
    else:
        if hive.status == HiveStatus.QUARANTINE:
            add("quarantine", "problem", "Улей на карантине")
        elif hive.status == HiveStatus.SICK:
            add("sick", "problem", "Семья болеет")
        if hive.status == HiveStatus.QUEENLESS or not queen:
            add("queenless", "problem", "Семья без матки" if hive.status == HiveStatus.QUEENLESS else "Матка не записана")
        if family.strength in _WEAK:
            add("weak", "attention", "Слабая семья")

        if latest is None:
            add("never_inspected", "attention", "Осмотров ещё не было")
        else:
            if latest.queen_present is False and latest.egg_laying is False and hive.status != HiveStatus.QUEENLESS:
                add("possible_queenless", "problem", "На последнем осмотре матки и яиц не было")
            if latest.swarming_signs or latest.queen_cells >= 3:
                add("swarming_risk", "attention", "Признаки роения на последнем осмотре")
            if latest.food_level == FoodLevel.CRITICAL:
                add("food_critical", "problem", "Корма критически мало")
            elif latest.food_level == FoodLevel.LOW:
                add("food_low", "attention", "Мало корма")
            if latest.health_status != InspectionHealth.HEALTHY and hive.status not in (HiveStatus.SICK, HiveStatus.QUARANTINE):
                add("health_suspicious", "attention", "На осмотре отмечено подозрение на болезнь")

        if hive.next_inspection_at and hive.next_inspection_at.date() < today:
            add("inspection_overdue", "attention", f"Осмотр просрочен на {_days((today - hive.next_inspection_at.date()).days)}")

    for c in cases:
        if c.status in ACTIVE_CASE_STATUSES:
            continue  # already reported through the hive status
        add("disease_suspected", "attention", f"Подозрение: {c.disease.name}")
    if not archived:
        for t in tasks:
            if t.due_date < today:
                add("task_overdue", "attention", f"Просрочено: {t.title}")

    verdict = "problem" if any(i.level == "problem" for i in issues) else "attention" if issues else "ok"
    issues.sort(key=lambda i: i.level != "problem")

    return HiveCheckOut(
        hive_id=hive.id, hive_number=hive.hive_number, apiary=ApiaryBrief.model_validate(hive.apiary),
        status=hive.status, is_archived=archived, verdict=verdict, headline=_HEADLINES[verdict], issues=issues,
        strength=family.strength if family else None,
        queen=CheckQueen(id=queen.id, queen_code=queen.queen_code, age_label=queen.age_label, status=queen.status) if queen else None,
        last_inspection=CheckInspection(
            id=latest.id, inspected_at=latest.inspected_at,
            days_ago=max(0, (today - latest.inspected_at.date()).days),
            user_name=latest.user.display_name if latest.user else None,
            strength=latest.strength, frames_total=latest.frames_total, brood_frames=latest.brood_frames,
            honey_frames=latest.honey_frames, pollen_frames=latest.pollen_frames, queen_present=latest.queen_present,
            egg_laying=latest.egg_laying, queen_cells=latest.queen_cells, swarming_signs=latest.swarming_signs,
            food_level=latest.food_level, health_status=latest.health_status,
        ) if latest else None,
        next_inspection_at=hive.next_inspection_at,
        open_cases=[CheckCase(disease_name=c.disease.name, status=CASE_STATUS[c.status]) for c in cases],
        open_tasks=[CheckTask(title=t.title, due_date=t.due_date, overdue=t.due_date < today) for t in tasks],
        honey_year_kg=honey_service.hive_honey(db, hive.id, today.year)["year_kg"],
    )
