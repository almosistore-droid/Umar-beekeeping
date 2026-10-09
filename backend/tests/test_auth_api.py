"""API tests for Telegram login, JWT sessions and role-based access."""
import time
import uuid

import jwt
from fastapi import Depends
from sqlalchemy import select

from app.auth.dependencies import ADMIN_ONLY, CAN_WRITE, require_roles
from app.auth.jwt import create_access_token
from app.main import app
from app.models.user import User, UserRole
from tests.conftest import make_init_data


# Throwaway endpoints to exercise RBAC dependencies
@app.get("/api/_test/admin", include_in_schema=False)
def _admin_only(user=Depends(require_roles(*ADMIN_ONLY))):
    return {"ok": True}


@app.get("/api/_test/write", include_in_schema=False)
def _write(user=Depends(require_roles(*CAN_WRITE))):
    return {"ok": True}


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "ok"}


def test_login_creates_user_with_default_role(client, db):
    r = client.post("/api/auth/telegram", json={"init_data": make_init_data(2000, start_param="hive_x")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["telegram_id"] == 2000
    assert body["user"]["role"] == "VIEWER"
    assert body["user"]["display_name"] == "Иван"
    assert body["start_param"] == "hive_x"
    assert db.scalar(select(User).where(User.telegram_id == 2000)) is not None


def test_admin_telegram_id_gets_admin_role(login):
    _, body = login(1000)
    assert body["user"]["role"] == "ADMIN"


def test_repeat_login_updates_profile_but_keeps_role(login, db):
    _, first = login(2000, first_name="Иван")
    user = db.get(User, uuid.UUID(first["user"]["id"]))
    user.role = UserRole.BEEKEEPER
    db.commit()

    _, second = login(2000, first_name="Иван Петрович", username="ivan_p")
    assert second["user"]["id"] == first["user"]["id"]
    assert second["user"]["first_name"] == "Иван Петрович"
    assert second["user"]["username"] == "ivan_p"
    assert second["user"]["role"] == "BEEKEEPER"


def test_forged_init_data_is_rejected(client, db):
    forged = make_init_data(1000, token="123:attacker-bot")
    r = client.post("/api/auth/telegram", json={"init_data": forged})
    assert r.status_code == 401
    assert "Telegram" in r.json()["detail"]
    assert db.scalar(select(User)) is None


def test_expired_init_data_is_rejected(client):
    r = client.post(
        "/api/auth/telegram",
        json={"init_data": make_init_data(2000, auth_date=int(time.time()) - 2 * 86400)},
    )
    assert r.status_code == 401


def test_empty_init_data_gives_readable_validation_error(client):
    r = client.post("/api/auth/telegram", json={"init_data": ""})
    assert r.status_code == 422
    assert r.json()["detail"].startswith("Проверьте введённые данные")


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_token(client, login):
    headers, body = login(2000)
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["id"] == body["user"]["id"]


def test_invalid_and_expired_tokens_rejected(client, login):
    _, body = login(2000)
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    expired = jwt.encode(
        {"sub": body["user"]["id"], "type": "access", "iat": 1, "exp": 2},
        "test-secret-test-secret-test-secret-0123",
        algorithm="HS256",
    )
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    other_key = jwt.encode(
        {"sub": body["user"]["id"], "type": "access", "iat": int(time.time()), "exp": int(time.time()) + 60},
        "some-other-secret-some-other-secret-xx",
        algorithm="HS256",
    )
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {other_key}"}).status_code == 401


def test_deactivated_user_is_blocked(client, login, db):
    headers, body = login(2000)
    user = db.get(User, uuid.UUID(body["user"]["id"]))
    user.is_active = False
    db.commit()
    assert client.get("/api/auth/me", headers=headers).status_code == 403
    r = client.post("/api/auth/telegram", json={"init_data": make_init_data(2000)})
    assert r.status_code == 403


def test_token_for_deleted_user_rejected(client):
    token, _ = create_access_token(uuid.uuid4(), "ADMIN")
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_rbac_roles(client, login, db):
    viewer_headers, _ = login(2000)
    admin_headers, _ = login(1000)
    assert client.get("/api/_test/admin", headers=viewer_headers).status_code == 403
    assert client.get("/api/_test/write", headers=viewer_headers).status_code == 403
    assert client.get("/api/_test/admin", headers=admin_headers).status_code == 200
    assert client.get("/api/_test/write", headers=admin_headers).status_code == 200


def test_role_change_applies_without_new_token(client, login, db):
    headers, body = login(2000)
    assert client.get("/api/_test/write", headers=headers).status_code == 403
    user = db.get(User, uuid.UUID(body["user"]["id"]))
    user.role = UserRole.ASSISTANT
    db.commit()
    assert client.get("/api/_test/write", headers=headers).status_code == 200


def test_openapi_docs_available(client):
    r = client.get("/api/openapi.json")
    assert r.status_code == 200
    assert "/api/auth/telegram" in r.json()["paths"]
