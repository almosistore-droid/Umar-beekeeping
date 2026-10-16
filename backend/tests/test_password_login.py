"""Login and password for people without Telegram: accounts made by the admin, temporary password, lockout."""
from datetime import datetime, timedelta, timezone

import pytest

from app.auth.passwords import hash_password, temporary_password, verify_password
from app.models import DeviceSession, User


@pytest.fixture
def admin(login):
    headers, _ = login(1000)
    return headers


def create(client, admin, login="karim", role="ASSISTANT", **kw):
    r = client.post("/api/admin/accounts", json={"first_name": "Карим", "login": login, "role": role, **kw}, headers=admin)
    assert r.status_code == 201, r.text
    return r.json()


def sign_in(client, login, password, device="Android · Chrome"):
    return client.post("/api/auth/password", json={"login": login, "password": password, "device_name": device})


def bearer(body):
    return {"Authorization": f"Bearer {body['access_token']}"}


def test_hashing():
    h = hash_password("секрет-123")
    assert h.startswith("scrypt$") and "секрет" not in h and h != hash_password("секрет-123")  # salted
    assert verify_password("секрет-123", h) and not verify_password("секрет-124", h)
    assert not verify_password("x", None) and not verify_password("x", "garbage")
    p = temporary_password()
    assert len(p) == 14 and p.count("-") == 2 and not set(p) & set("0o1li")


def test_admin_creates_account_and_person_changes_password(client, admin, db):
    acc = create(client, admin, login=" Karim.Bee ")
    assert acc["login"] == "karim.bee" and acc["user"]["telegram_id"] is None
    assert acc["user"]["must_change_password"] is True and acc["user"]["has_password"] is True
    temp = acc["temporary_password"]
    assert db.query(User).filter_by(login="karim.bee").one().password_hash != temp

    body = sign_in(client, "KARIM.BEE", temp).json()
    assert body["status"] == "ok" and body["device_token"] and body["user"]["role"] == "ASSISTANT"
    # until the temporary password is changed, only the profile endpoints work
    r = client.get("/api/hives", headers=bearer(body))
    assert r.status_code == 403 and r.json()["detail"] == "Сначала смените временный пароль"
    assert client.get("/api/auth/me", headers=bearer(body)).status_code == 200

    r = client.put("/api/auth/me/password", json={"current_password": temp, "new_password": "short"}, headers=bearer(body))
    assert r.status_code == 422 and "8 символов" in r.json()["detail"]
    r = client.put("/api/auth/me/password", json={"current_password": "wrong-one", "new_password": "pchela-2026"},
                   headers=bearer(body))
    assert r.status_code == 422 and "Текущий пароль" in r.json()["detail"]
    r = client.put("/api/auth/me/password", json={"current_password": temp, "new_password": "pchela-2026"}, headers=bearer(body))
    assert r.status_code == 200 and r.json()["must_change_password"] is False
    assert client.get("/api/hives", headers=bearer(body)).status_code == 200
    assert sign_in(client, "karim.bee", temp).status_code == 401
    assert sign_in(client, "karim.bee", "pchela-2026").status_code == 200

    # the device token keeps the phone logged in, like after a Telegram login
    r = client.post("/api/auth/device", json={"device_token": body["device_token"]})
    assert r.status_code == 200 and r.json()["user"]["login"] == "karim.bee"


def test_wrong_password_same_answer_and_lockout(client, admin, db):
    acc = create(client, admin)
    unknown = sign_in(client, "nobody", "whatever")
    wrong = sign_in(client, "karim", "whatever")
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"] == "Неверный логин или пароль"
    for _ in range(4):
        assert sign_in(client, "karim", "nope").status_code == 401
    r = sign_in(client, "karim", acc["temporary_password"])  # even the right password waits now
    assert r.status_code == 429 and "15 мин" in r.json()["detail"]
    db.query(User).filter_by(login="karim").update({"locked_until": datetime.now(timezone.utc) - timedelta(seconds=1)})
    db.commit()
    assert sign_in(client, "karim", acc["temporary_password"]).status_code == 200


def test_blocked_account(client, admin, db):
    acc = create(client, admin)
    client.patch(f"/api/users/{acc['user']['id']}", json={"is_active": False}, headers=admin)
    assert sign_in(client, "karim", "wrong").json()["detail"] == "Неверный логин или пароль"  # nothing leaked
    r = sign_in(client, "karim", acc["temporary_password"])
    assert r.status_code == 403 and r.json()["detail"] == "Учётная запись отключена"


def test_login_rules(client, admin):
    create(client, admin, login="karim")
    r = client.post("/api/admin/accounts", json={"first_name": "Другой", "login": "Karim", "role": "VIEWER"}, headers=admin)
    assert r.status_code == 409 and r.json()["detail"] == "Этот логин уже занят"
    for bad in ("ab", "карим", "a b", "-start"):
        r = client.post("/api/admin/accounts", json={"first_name": "X", "login": bad, "role": "VIEWER"}, headers=admin)
        assert r.status_code == 422 and "Логин" in r.json()["detail"]


def test_reset_password_logs_out_everywhere(client, admin, db):
    acc = create(client, admin)
    first = sign_in(client, "karim", acc["temporary_password"]).json()
    r = client.post(f"/api/admin/users/{acc['user']['id']}/password", json={}, headers=admin)
    assert r.status_code == 200 and r.json()["temporary_password"] != acc["temporary_password"]
    assert client.post("/api/auth/device", json={"device_token": first["device_token"]}).status_code == 401
    assert sign_in(client, "karim", acc["temporary_password"]).status_code == 401
    assert sign_in(client, "karim", r.json()["temporary_password"]).json()["user"]["must_change_password"] is True
    assert db.query(DeviceSession).filter(DeviceSession.revoked_at.is_(None)).count() == 1


def test_telegram_user_gets_a_password_too(client, admin, login):
    _, tg = login(2500, username="umar_tg")
    r = client.post(f"/api/admin/users/{tg['user']['id']}/password", json={}, headers=admin)
    assert r.status_code == 422 and "логин" in r.json()["detail"]
    r = client.post(f"/api/admin/users/{tg['user']['id']}/password", json={"login": "umar"}, headers=admin)
    assert r.status_code == 200 and r.json()["login"] == "umar"
    body = sign_in(client, "umar", r.json()["temporary_password"]).json()
    assert body["user"]["id"] == tg["user"]["id"] and body["user"]["telegram_id"] == 2500  # one account, two ways in


def test_admin_cannot_reset_own_password_here(client, admin, db):
    me = db.query(User).filter_by(telegram_id=1000).one()
    r = client.post(f"/api/admin/users/{me.id}/password", json={"login": "boss"}, headers=admin)
    assert r.status_code == 409 and "Ещё → Сменить пароль" in r.json()["detail"]


def test_only_admin_manages_accounts(client, as_role):
    for role in ("BEEKEEPER", "ASSISTANT", "VIEWER"):
        r = client.post("/api/admin/accounts", json={"first_name": "X", "login": "xxx", "role": "VIEWER"}, headers=as_role(role))
        assert r.status_code == 403


def test_reports_by_bot_need_telegram(client, admin):
    acc = create(client, admin, role="BEEKEEPER")
    temp = acc["temporary_password"]
    body = sign_in(client, "karim", temp).json()
    client.put("/api/auth/me/password", json={"current_password": temp, "new_password": "pchela-2026"}, headers=bearer(body))
    from app.schemas.common import today
    r = client.post(f"/api/reports/yearly/{today().year}/send", params={"format": "pdf"}, headers=bearer(body))
    assert r.status_code == 409 and "Скачать" in r.json()["detail"]
    r = client.get(f"/api/reports/yearly/{today().year}/export", params={"format": "pdf"}, headers=bearer(body))
    assert r.status_code == 200  # downloading works


def test_audit_entries(client, admin):
    acc = create(client, admin)
    sign_in(client, "karim", acc["temporary_password"])
    log = client.get("/api/admin/audit", params={"entity_type": "user"}, headers=admin).json()["items"]
    actions = {e["action"] for e in log}
    assert {"account_created", "device_login"} <= actions
    entry = next(e for e in log if e["action"] == "account_created")
    assert entry["new_value"]["login"] == "karim" and "password" not in str(entry["new_value"]).lower()


def test_errors_in_tajik(client):
    r = client.post("/api/auth/password", json={"login": "x", "password": "y"}, headers={"X-Lang": "tg"})
    assert r.json()["detail"] == "Логин ё парол нодуруст аст"
