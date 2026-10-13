from sqlalchemy import func, select

from app.models import Apiary, Hive, Queen
from app.utils import seed


def test_seed_is_valid_and_idempotent(db):
    seed.run(None)
    seed.run(None)
    assert db.scalar(select(func.count()).select_from(Apiary)) == 2
    assert db.scalar(select(func.count()).select_from(Hive)) == 11  # + split
    assert db.scalar(select(func.count()).select_from(Queen)) == 10


def test_seed_adds_health_records_once(db):
    from app.models import Feeding, HiveDisease, Inspection, Task, Treatment
    seed.run(None)
    counts = [db.scalar(select(func.count()).select_from(m)) for m in (Inspection, HiveDisease, Treatment, Feeding)]
    seed.run(None)
    again = [db.scalar(select(func.count()).select_from(m)) for m in (Inspection, HiveDisease, Treatment, Feeding)]
    assert counts == again and all(counts)
    assert db.scalar(select(func.count()).select_from(Task).where(Task.status == "OPEN")) >= 2


def test_seed_adds_operations_once(db):
    from app.models import HiveMovement, HiveSplit, HoneyHarvest, OtherProduct, Wintering
    seed.run(None)
    models = (HoneyHarvest, OtherProduct, Wintering, HiveSplit, HiveMovement)
    counts = [db.scalar(select(func.count()).select_from(m)) for m in models]
    seed.run(None)
    assert counts == [db.scalar(select(func.count()).select_from(m)) for m in models] and all(counts)


def test_seed_adds_crm_once(db):
    from app.models import Customer, Expense, Order, Payment, Sale
    from app.services import crm_service
    seed.run(None)
    models = (Customer, Expense, Sale, Payment, Order)
    counts = [db.scalar(select(func.count()).select_from(m)) for m in models]
    seed.run(None)
    assert counts == [db.scalar(select(func.count()).select_from(m)) for m in models] and all(counts)
    debtors = crm_service.debts(db)
    assert len(debtors) == 2 and all(d.debt > 0 for d in debtors)
