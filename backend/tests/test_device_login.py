"""App on the phone outside Telegram: login confirmed in the bot, device sessions, logout."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.auth.bot_signature import bot_signature
from app.config import get_settings
from app.models import DeviceSession, LoginCode, User, UserRole

BOT = {"X-Bot-Auth": bot_signature("7000000000:TEST-token-for-unit-tests")}
TG = {"id": 5100, "first_name": "Карим", "username": "karim_bee", "language_code": "tg"}


@pytest.fixture(autouse=True)
def bot_username(monkeypatch):
    monkeypatch.setattr(get_settings(), "telegram_bot_username", "fayzi_bee_bot")


def start(client, name="iPhone · Safari"):
    r = client.post("/api/auth/login-codes", json={"device_name": name})
    assert r.status_code == 201, r.text
    return r.json()


def confirm(client, code, user=TG, headers=BOT):
    return client.post("/api/auth/login-codes/confirm", json={"code": code, "user": user}, headers=headers)


def poll(client, c, secret=None):
    return client.post("/api/auth/login-codes/poll", json={"code": c["code"], "poll_secret": secret or c["poll_secret"]})


def full_login(client, user=TG):
    c = start(client)
    assert confirm(client, c["code"], user).status_code == 200
    body = poll(client, c).json()
    assert body["status"] == "ok"
    return body


def test_whole_flow(client):
    c = start(client)
    assert c["bot_link"] == f"https://t.me/fayzi_bee_bot?start=login_{c['code']}" and c["expires_in"] == 300
    assert len("login_" + c["code"]) <= 64  # Telegram's start parameter limit
    assert poll(client, c).json() == {"status": "pending", "access_token": None, "token_type": "bearer",
                                      "expires_in": None, "device_token": None, "user": None}
    r = confirm(client, c["code"])
    assert r.status_code == 200 and r.json()["display_name"] == "Карим"
    body = poll(client, c).json()
    assert body["status"] == "ok" and body["access_token"] and body["device_token"]
    assert body["user"]["telegram_id"] == 5100 and body["user"]["role"] == "VIEWER"
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200 and me.json()["username"] == "karim_bee"
    assert poll(client, c).json()["status"] == "expired"  # one-time: the session is handed out once


def test_same_account_as_mini_app(client, login):
    _, mini = login(5100, username="karim_bee")
    assert full_login(client)["user"]["id"] == mini["user"]["id"]


def test_admin_ids_and_invites_apply(client):
    assert full_login(client, {**TG, "id": 1000})["user"]["role"] == "ADMIN"


def test_only_the_requesting_device_collects(client):
    c = start(client)
    confirm(client, c["code"])
    r = poll(client, c, secret="x" * 40)
    assert r.status_code == 404 and r.json()["detail"] == "Код входа не найден"
    assert poll(client, c).json()["status"] == "ok"  # the real device still can


def test_bot_signature_required(client):
    c = start(client)
    assert confirm(client, c["code"], headers={}).status_code == 403
    assert confirm(client, c["code"], headers={"X-Bot-Auth": "0" * 64}).status_code == 403
    assert client.post("/api/auth/login-codes/deny", json={"code": c["code"]}).status_code == 403
    assert poll(client, c).json()["status"] == "pending"


def test_deny(client):
    c = start(client)
    assert client.post("/api/auth/login-codes/deny", json={"code": c["code"]}, headers=BOT).status_code == 204
    assert poll(client, c).json()["status"] == "denied"
    assert confirm(client, c["code"]).status_code == 409


def test_code_is_one_time_and_expires(client, db):
    c = start(client)
    assert confirm(client, c["code"]).status_code == 200
    assert confirm(client, c["code"], {**TG, "id": 5200}).status_code == 409  # nobody can re-confirm it

    late = start(client)
    db.query(LoginCode).filter(LoginCode.status == "PENDING").update(
        {"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)})
    db.commit()
    assert poll(client, late).json()["status"] == "expired"
    r = confirm(client, late["code"])
    assert r.status_code == 410 and "устарел" in r.json()["detail"]
    assert confirm(client, "A" * 32).status_code == 404


def test_codes_stored_hashed(client, db):
    c = start(client)
    row = db.query(LoginCode).one()
    assert c["code"] not in (row.code_hash, row.poll_hash) and len(row.code_hash) == 64
    body = full_login(client)
    assert all(body["device_token"] != s.token_hash for s in db.query(DeviceSession))


def test_device_session_next_launch_and_logout(client, db):
    body = full_login(client)
    r = client.post("/api/auth/device", json={"device_token": body["device_token"]})
    assert r.status_code == 200 and r.json()["user"]["telegram_id"] == 5100 and r.json()["access_token"]
    assert db.query(DeviceSession).one().name == "iPhone · Safari"
    assert client.post("/api/auth/logout", json={"device_token": body["device_token"]}).status_code == 204
    r = client.post("/api/auth/device", json={"device_token": body["device_token"]})
    assert r.status_code == 401 and "Войдите снова" in r.json()["detail"]


def test_idle_device_expires(client, db):
    body = full_login(client)
    db.query(DeviceSession).update({"last_used_at": datetime.now(timezone.utc) - timedelta(days=181)})
    db.commit()
    assert client.post("/api/auth/device", json={"device_token": body["device_token"]}).status_code == 401


def test_blocked_user(client, db):
    body = full_login(client)
    db.query(User).filter_by(telegram_id=5100).update({"is_active": False})
    db.commit()
    r = client.post("/api/auth/device", json={"device_token": body["device_token"]})
    assert r.status_code == 403 and r.json()["detail"] == "Учётная запись отключена"
    assert confirm(client, start(client)["code"]).status_code == 403


def test_role_change_applies_on_device(client, db):
    body = full_login(client)
    db.query(User).filter_by(telegram_id=5100).update({"role": UserRole.BEEKEEPER})
    db.commit()
    r = client.post("/api/auth/device", json={"device_token": body["device_token"]})
    assert r.json()["user"]["role"] == "BEEKEEPER"


def test_device_login_audited(client, as_role):
    full_login(client)
    log = client.get("/api/admin/audit", params={"entity_type": "user"}, headers=as_role("ADMIN", 999)).json()["items"]
    assert any(e["action"] == "device_login" and e["new_value"]["device"] == "iPhone · Safari" for e in log)


def test_not_configured_without_bot_username(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "telegram_bot_username", "")
    r = client.post("/api/auth/login-codes", json={})
    assert r.status_code == 503 and "TELEGRAM_BOT_USERNAME" in r.json()["detail"]


def test_errors_in_tajik(client):
    r = client.post("/api/auth/device", json={"device_token": "x" * 40}, headers={"X-Lang": "tg"})
    assert r.status_code == 401 and r.json()["detail"] == "Воридшавӣ дар ин дастгоҳ дигар эътибор надорад. Аз нав ворид шавед."


def test_bot_has_the_same_signature():
    """bot/signing.py (inside the bot image) must compute exactly what the backend checks."""
    import importlib.util
    path = Path(__file__).resolve().parents[2] / "bot" / "signing.py"
    spec = importlib.util.spec_from_file_location("bot_signing", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.bot_signature("123:abc") == bot_signature("123:abc")
