from sqlalchemy import func, select

from app.models import Apiary, Hive, Queen
from app.utils import seed


def test_seed_is_valid_and_idempotent(db):
    seed.run(None)
    seed.run(None)
    assert db.scalar(select(func.count()).select_from(Apiary)) == 2
    assert db.scalar(select(func.count()).select_from(Hive)) == 10
    assert db.scalar(select(func.count()).select_from(Queen)) == 10
