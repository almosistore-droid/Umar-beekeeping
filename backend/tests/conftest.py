"""Test setup: a dedicated PostgreSQL database, migrated with Alembic (not create_all),
so every test run also proves the migrations work."""
import json
import os
import time
import uuid

# Must be set before the app is imported
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://bee:bee@localhost:5432/beekeeping_test"
)
os.environ["TELEGRAM_BOT_TOKEN"] = "7000000000:TEST-token-for-unit-tests"
os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret-0123"
os.environ["ADMIN_TELEGRAM_IDS"] = "1000"
os.environ["DEFAULT_USER_ROLE"] = "VIEWER"

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.auth.telegram import sign_init_data
from app.config import get_settings
from app.database import SessionLocal, engine
from app.main import app

BACKEND_DIR = os.path.dirname(os.path.dirname(__file__))


@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield cfg


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    with engine.begin() as conn:
        # Reference data seeded by migrations (disease catalog) is kept; only custom entries are removed
        tables = conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname='public' "
                 "AND tablename NOT IN ('alembic_version', 'diseases')")
        ).scalars().all()
        if tables:
            conn.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"))
        conn.execute(text("DELETE FROM diseases WHERE code LIKE 'CUSTOM_%'"))


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def make_init_data(telegram_id: int = 2000, *, first_name: str = "Иван", username: str | None = "ivan",
                   auth_date: int | None = None, start_param: str | None = None,
                   token: str | None = None) -> str:
    user = {"id": telegram_id, "first_name": first_name}
    if username:
        user["username"] = username
    fields = {
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": json.dumps(user, ensure_ascii=False, separators=(",", ":")),
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
    }
    if start_param:
        fields["start_param"] = start_param
    return sign_init_data(fields, token or get_settings().telegram_bot_token)


@pytest.fixture
def login(client):
    def _login(telegram_id: int = 2000, **kw):
        r = client.post("/api/auth/telegram", json={"init_data": make_init_data(telegram_id, **kw)})
        assert r.status_code == 200, r.text
        body = r.json()
        return {"Authorization": f"Bearer {body['access_token']}"}, body
    return _login


@pytest.fixture
def as_role(login, db):
    """Headers for a fresh user with the given role, e.g. as_role("BEEKEEPER")."""
    from app.models.user import User, UserRole
    counter = iter(range(5000, 6000))

    def _as(role: str, telegram_id: int | None = None):
        headers, body = login(telegram_id or next(counter))
        user = db.get(User, uuid.UUID(body["user"]["id"]))
        user.role = UserRole(role)
        db.commit()
        return headers
    return _as


@pytest.fixture
def beekeeper(as_role):
    return as_role("BEEKEEPER", 3000)
