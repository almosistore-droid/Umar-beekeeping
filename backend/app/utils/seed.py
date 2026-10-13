"""Demo data for trying out the interface.

    python -m app.utils.seed                # owner = first id in ADMIN_TELEGRAM_IDS
    python -m app.utils.seed --telegram-id 123456789

Goes through the same services as the API, so history and audit entries are real.
Safe to run twice: each block runs only if its demo data is missing, so running it
again after an update adds the new stage's demo records to an existing demo apiary.
"""
import argparse
import random
from datetime import date, timedelta

from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import Apiary, FamilyOrigin, FamilyStrength, HiveType, QueenOrigin, User, UserRole
from app.schemas.apiary import ApiaryCreate
from app.schemas.hive import FamilyCreate, HiveCreate
from app.schemas.queen import AssignQueenRequest, QueenCreate
from app.services import apiary_service, hive_service, queen_service

DEMO_APIARIES = [
    ("Пасека №1 (демо)", "Основная пасека у дома", "Варзобское ущелье", 38.75, 68.82),
    ("Горная пасека (демо)", "Летняя кочёвка на разнотравье", "Ромит", 38.73, 69.30),
]
BREEDS = ["Карника", "Карпатка", "Бакфаст", "Среднерусская", "Кавказская"]


def run(telegram_id: int | None) -> None:
    settings = get_settings()
    if settings.environment == "production" and not telegram_id:
        raise SystemExit("В production укажите --telegram-id явно")
    tg_id = telegram_id or (settings.admin_telegram_ids[0] if settings.admin_telegram_ids else 100000001)

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.telegram_id == tg_id))
        if user is None:
            user = User(telegram_id=tg_id, first_name="Демо", last_name="Пчеловод", role=UserRole.ADMIN)
            db.add(user)
            db.commit()

        if db.scalar(select(Apiary.id).where(Apiary.name == DEMO_APIARIES[0][0])):
            print("Демо-пасеки уже есть.")
        else:
            _seed_structure(db, user)
        _seed_health(db, user)
    finally:
        db.close()


def _seed_structure(db, user) -> None:
    """Stage 2 demo: 2 apiaries, 10 hives, queens with one replacement in history."""
    rnd = random.Random(42)
    today = date.today()
    apiaries = [
        apiary_service.create_apiary(
            db, ApiaryCreate(name=n, description=d, address=a, latitude=lat, longitude=lon), user)
        for n, d, a, lat, lon in DEMO_APIARIES
    ]

    strengths = list(FamilyStrength)
    for i in range(1, 11):
        apiary = apiaries[0] if i <= 7 else apiaries[1]
        empty = i == 10
        hive = hive_service.create_hive(db, HiveCreate(
            apiary_id=apiary.id, hive_number=str(i),
            hive_type=HiveType.DADANT if i % 3 else HiveType.LANGSTROTH,
            installation_date=today.replace(year=today.year - 2, month=4, day=1),
            family=None if empty else FamilyCreate(
                strength=strengths[(i + 1) % 5], origin=rnd.choice(list(FamilyOrigin)[:5]),
                start_date=today.replace(year=today.year - 1, month=5, day=1) + timedelta(days=i)),
        ), user)
        if empty or i == 6:  # hive 6 is left queenless for the demo
            if i == 6:
                hive_service.update_hive(db, hive, hive_service.HiveUpdate(status="QUEENLESS"), user)
            continue
        birth = today.replace(year=today.year - (i % 3), month=6, day=1) - timedelta(days=i * 5)
        queen = queen_service.create_queen(db, QueenCreate(
            queen_code=f"M-{100 + i}", birth_date=birth, breed=rnd.choice(BREEDS),
            origin=rnd.choice([QueenOrigin.OWN_BRED, QueenOrigin.PURCHASED, QueenOrigin.SUPERSEDURE]),
            egg_laying_quality=rnd.randint(3, 5), swarming_tendency=rnd.randint(1, 4),
            temperament=rnd.randint(2, 5)), user)
        queen_service.assign_queen(db, hive, AssignQueenRequest(
            queen_id=queen.id, installed_at=max(birth + timedelta(days=20),
                                                hive.current_family.start_date)), user)

    # One spare queen waiting in a nucleus box, one replacement for history
    queen_service.create_queen(db, QueenCreate(queen_code="M-200", birth_date=today - timedelta(days=60),
                                               breed="Карника", origin=QueenOrigin.OWN_BRED), user)
    hive1 = hive_service.repo.list_hives(db, apiary_id=apiaries[0].id, q="1")[0][0]
    replacement = queen_service.create_queen(db, QueenCreate(
        queen_code="M-201", birth_date=today - timedelta(days=90), breed="Бакфаст",
        origin=QueenOrigin.PURCHASED), user)
    queen_service.assign_queen(db, hive1, AssignQueenRequest(
        queen_id=replacement.id, installed_at=today - timedelta(days=30),
        removal_reason="Плохая яйценоскость"), user)
    print("Готово: 2 пасеки, 10 ульев, 10 маток.")


def _seed_health(db, user) -> None:
    """Stage 3 demo: weekly inspections, a varroosis case with treatments, feedings."""
    from datetime import datetime, time, timezone

    from app.models import Disease, Hive, Inspection
    from app.schemas.health import CaseCreate, CaseUpdate, FeedingCreate, InspectionCreate, TreatmentCreate
    from app.services import health_service, inspection_service

    demo_apiary_ids = select(Apiary.id).where(Apiary.name.in_([a[0] for a in DEMO_APIARIES]))
    hives = db.scalars(select(Hive).where(Hive.apiary_id.in_(demo_apiary_ids),
                                          Hive.current_family_id.is_not(None))
                       .order_by(Hive.hive_number)).unique().all()
    if not hives or db.scalar(select(Inspection.id).where(Inspection.hive_id.in_([h.id for h in hives])).limit(1)):
        print("Демо-записи осмотров уже есть." if hives else "Нет демо-ульев для осмотров.")
        return

    rnd = random.Random(7)
    today = date.today()
    strengths = list(FamilyStrength)
    for n, hive in enumerate(hives):
        for weeks_ago in (5, 3, 1):
            when = datetime.combine(today - timedelta(days=weeks_ago * 7 + n % 3), time(9, 30), tzinfo=timezone.utc)
            total = rnd.choice([8, 10, 12])
            brood = rnd.randint(3, min(7, total))
            honey = rnd.randint(1, total - brood)
            pollen = rnd.randint(0, total - brood - honey)
            queen_seen = not (hive.status.value == "QUEENLESS")
            inspection_service.create_inspection(db, hive.id, InspectionCreate(
                inspected_at=when, strength=strengths[min(4, max(0, (n + 3 - weeks_ago // 2) % 5))],
                frames_total=total, brood_frames=brood, honey_frames=honey, pollen_frames=pollen,
                queen_present=queen_seen, egg_laying=queen_seen, food_level=rnd.choice(["LOW", "NORMAL", "ABUNDANT"]),
                aggressiveness=rnd.randint(1, 4), queen_cells=rnd.choice([0, 0, 0, 2])), user)

    varroa = db.scalar(select(Disease).where(Disease.code == "VARROOSIS"))
    sick_hive = hives[1]
    case, _ = health_service.create_case(db, sick_hive.id, CaseCreate(
        disease_id=varroa.id, detected_at=today - timedelta(days=18), status="CONFIRMED", severity="MODERATE",
        symptoms="Клещ на пчёлах, деформированные крылья"), user)
    health_service.create_treatment(db, sick_hive.id, TreatmentCreate(
        treated_at=today - timedelta(days=14), hive_disease_id=case.id, medication="Бипин", dosage="1 мл на улочку",
        method="Полив", next_treatment_date=today - timedelta(days=7)), user)
    health_service.create_treatment(db, sick_hive.id, TreatmentCreate(
        treated_at=today - timedelta(days=7), hive_disease_id=case.id, medication="Бипин", dosage="1 мл на улочку",
        method="Полив", result="Осыпь клеща уменьшилась", next_treatment_date=today + timedelta(days=3)), user)

    healed_hive = hives[2]
    old_case, _ = health_service.create_case(db, healed_hive.id, CaseCreate(
        disease_id=varroa.id, detected_at=today - timedelta(days=60), status="TREATING", severity="LIGHT"), user)
    health_service.update_case(db, old_case.id, CaseUpdate(status="RESOLVED", resolved_at=today - timedelta(days=40)), user)

    for hive in hives[:4]:
        health_service.create_feeding(db, hive.id, FeedingCreate(
            fed_at=today - timedelta(days=12), feed_type="SUGAR_SYRUP", quantity=2, unit="L",
            reason="Осенняя подкормка", next_feeding_date=today + timedelta(days=2)), user)
    print(f"Готово: осмотры для {len(hives)} ульев, варроатоз с обработками, подкормки.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Загрузить демо-данные")
    parser.add_argument("--telegram-id", type=int, default=None)
    run(parser.parse_args().telegram_id)
