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
from app.schemas.common import today as app_today
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
        _seed_operations(db, user)
        _seed_crm(db, user)
    finally:
        db.close()


def _seed_structure(db, user) -> None:
    """Stage 2 demo: 2 apiaries, 10 hives, queens with one replacement in history."""
    rnd = random.Random(42)
    today = app_today()
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
    today = app_today()
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


def _seed_operations(db, user) -> None:
    """Stage 4 demo: honey over two seasons, products, last winter, one split, one move."""
    from app.models import Hive, HoneyHarvest
    from app.schemas.operations import (HarvestCreate, MoveRequest, ProductCreate, SplitCreate, WinteringFinish,
                                        WinteringStart)
    from app.services import honey_service, operations_service

    demo_ids = select(Apiary.id).where(Apiary.name.in_([a[0] for a in DEMO_APIARIES]))
    hives = db.scalars(select(Hive).where(Hive.apiary_id.in_(demo_ids), Hive.current_family_id.is_not(None))
                       .order_by(Hive.hive_number)).unique().all()
    if not hives or db.scalar(select(HoneyHarvest.id).where(HoneyHarvest.hive_id.in_([h.id for h in hives])).limit(1)):
        print("Демо-записи мёда уже есть." if hives else "Нет демо-ульев для мёда.")
        return

    rnd = random.Random(11)
    today = app_today()
    kinds = ["Разнотравье", "Акация", "Горный", "Подсолнечник", "Эспарцет"]
    for year in (today.year - 1, today.year):
        for hive in hives:
            for month, day in ((6, 10), (7, 25), (8, 28)):
                when = date(year, month, day)
                if when > today or rnd.random() < 0.25:
                    continue
                honey_service.create_harvest(db, hive.id, HarvestCreate(
                    harvest_date=when, honey_type=rnd.choice(kinds), frames_count=rnd.randint(3, 8),
                    weight_kg=round(rnd.uniform(6, 18), 1), price_per_kg=rnd.choice([70, 80, 90])), user)

    honey_service.create_product(db, ProductCreate(product_type="WAX", collected_at=date(today.year, 8, 30),
                                                   quantity=3.5, unit="KG", price_per_unit=150,
                                                   apiary_id=hives[0].apiary_id), user)
    honey_service.create_product(db, ProductCreate(product_type="PROPOLIS", collected_at=date(today.year, 9, 5),
                                                   quantity=240, unit="G", price_per_unit=2, hive_id=hives[0].id), user)

    season = f"{today.year - 1}/{today.year}"
    for hive in hives[:3]:
        w = operations_service.start_wintering(db, hive.id, WinteringStart(
            season=season, pre_winter_strength="STRONG", food_kg=18, frames_count=8, winter_location="На точке",
            pre_winter_treatment="Щавелевая кислота", start_date=date(today.year - 1, 10, 25)), user)
        operations_service.finish_wintering(db, w.id, WinteringFinish(
            end_date=date(today.year, 3, 20), result="STRONG"), user)

    source = hives[2]
    if not db.scalar(select(Hive.id).where(Hive.apiary_id == source.apiary_id, Hive.hive_number == "11")):
        operations_service.split_hive(db, source.id, SplitCreate(
            new_hive_number="11", split_date=today - timedelta(days=40), notes="Отводок на плодную матку"), user)

    mountain = db.scalar(select(Apiary).where(Apiary.name == DEMO_APIARIES[1][0]))
    mover = next((h for h in hives if h.apiary_id != mountain.id and h.hive_number == "7"), None)
    if mover:
        operations_service.move_hive(db, mover.id, MoveRequest(to_apiary_id=mountain.id, reason="Кочёвка на горное разнотравье",
                                                               movement_date=today - timedelta(days=30)), user)
    print("Готово: мёд за два сезона, воск и прополис, зимовка, отводок, кочёвка.")



def _seed_crm(db, user) -> None:
    """Stage 7 demo: customers, a year of expenses, sales (paid, partly paid, on credit), open orders."""
    from app.models import Customer
    from app.schemas.crm import CustomerIn, DeliverIn, ExpenseIn, LineIn, OrderCreate, PaymentIn, SaleCreate
    from app.services import crm_service as crm

    if db.scalar(select(Customer.id).where(Customer.name.like("% (демо)")).limit(1)):
        print("Демо-данные CRM уже есть.")
        return
    today = app_today()

    def back(days: int) -> date:
        return max(today - timedelta(days=days), date(today.year, 1, 1))

    people = [("Фарход Саидов (демо)", "+992901112233", "Душанбе", "Берёт горный мёд каждый месяц"),
              ("Зарина Каримова (демо)", "+992935554466", "Худжанд", None),
              ("Магазин «Асал» (демо)", "+992987770011", "Душанбе", "Оптовый покупатель, оплата частями"),
              ("Рустам (демо)", None, "Вахдат", None)]
    customers = [crm.create_customer(db, CustomerIn(name=n, phone=p, city=c, notes=x), user) for n, p, c, x in people]

    for days, cat, amount, text in [(250, "FOUNDATION", 600, "Вощина 10 кг"), (220, "MEDICINE", 340, "Бипин, Апиварол"),
                                    (180, "FRAMES", 900, "Рамки 60 шт"), (150, "FEED", 1200, "Сахар 100 кг"),
                                    (120, "FUEL", 450, "Бензин на кочёвку"), (95, "EQUIPMENT", 1500, "Медогонка, ремонт"),
                                    (60, "TRANSPORT", 800, "Перевозка ульев в горы"), (30, "QUEENS", 1000, "Плодные матки 4 шт"),
                                    (10, "FEED", 700, "Канди на зиму")]:
        crm.create_expense(db, ExpenseIn(expense_date=back(days), category=cat, amount=amount, description=text), user)

    honey = lambda kg, price: LineIn(category="HONEY", quantity=kg, unit="KG", price_per_unit=price)
    sales = [(80, customers[0], [honey(5, 90)], "full", None),
             (70, customers[2], [honey(30, 75), LineIn(category="WAX", quantity=2, unit="KG", price_per_unit=150)], "partial", 1500),
             (45, customers[1], [honey(3, 95)], "full", None),
             (40, None, [honey(2, 100)], "full", None),
             (25, customers[0], [honey(4, 90), LineIn(category="PROPOLIS", quantity=50, unit="G", price_per_unit=3)], "credit", None),
             (12, customers[2], [honey(20, 75)], "partial", 500)]
    created = [crm.create_sale(db, SaleCreate(sale_date=back(d), customer_id=c.id if c else None, items=items,
                                              payment=pay, paid_amount=amount), user) for d, c, items, pay, amount in sales]
    crm.add_payment(db, created[1], PaymentIn(amount=600, paid_at=back(30), method="TRANSFER"), user)

    crm.create_order(db, OrderCreate(customer_id=customers[1].id, items=[honey(6, 95)], due_date=today + timedelta(days=5),
                                     notes="Две банки по 3 л, горный"), user)
    ready = crm.create_order(db, OrderCreate(customer_id=customers[3].id, order_date=back(6), items=[honey(10, 85)],
                                             due_date=back(1)), user)
    from app.schemas.crm import OrderUpdate
    crm.update_order(db, ready, OrderUpdate(status="READY"), user)
    done = crm.create_order(db, OrderCreate(customer_id=customers[0].id, order_date=back(20), items=[honey(3, 90)]), user)
    crm.deliver_order(db, done, DeliverIn(sale_date=back(18)), user)
    print("Готово: клиенты, расходы за год, продажи с долгами, заказы.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Загрузить демо-данные")
    parser.add_argument("--telegram-id", type=int, default=None)
    run(parser.parse_args().telegram_id)
