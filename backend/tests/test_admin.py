"""Admin panel: invitations (role on first login), access, system overview, activity log."""
from datetime import datetime, timedelta, timezone

import pytest

from app.models import InviteStatus, UserInvite


@pytest.fixture
def admin(login):
    headers, _ = login(1000)  # ADMIN_TELEGRAM_IDS=1000 in conftest
    return headers


def invite(client, admin, **body):
    return client.post("/api/admin/invites", json=body, headers=admin)


def me(login, telegram_id, **kw):
    _, body = login(telegram_id, **kw)
    return body["user"]


def test_invite_by_id_gives_role_on_first_login(client, admin, login):
    r = invite(client, admin, telegram_id=7001, role="BEEKEEPER", note="Сосед Карим")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["kind"] == "invited" and body["invite"]["status"] == "PENDING" and body["invite"]["note"] == "Сосед Карим"
    assert "пчеловод" in body["share_text"]
    user = me(login, 7001, username="karim")
    assert user["role"] == "BEEKEEPER"
    inv = client.get("/api/admin/invites", headers=admin).json()[0]
    assert inv["status"] == "USED" and inv["used_by_name"] and inv["used_at"]
    log = client.get("/api/admin/audit", params={"entity_type": "user"}, headers=admin).json()["items"]
    assert any(e["action"] == "joined_by_invite" and e["new_value"]["role"] == "BEEKEEPER" for e in log)


def test_invite_by_username_case_and_at_sign(client, admin, login):
    r = invite(client, admin, username=" @Ivan_Pchel ", role="ASSISTANT")
    assert r.status_code == 201 and r.json()["invite"]["username"] == "ivan_pchel"
    assert me(login, 7002, username="IVAN_pchel")["role"] == "ASSISTANT"


def test_id_wins_over_username(client, admin, login):
    invite(client, admin, telegram_id=7003, role="BEEKEEPER")
    invite(client, admin, username="same_person", role="VIEWER")
    assert me(login, 7003, username="same_person")["role"] == "BEEKEEPER"
    statuses = {i["role"]: i["status"] for i in client.get("/api/admin/invites", headers=admin).json()}
    assert statuses == {"BEEKEEPER": "USED", "VIEWER": "PENDING"}


def test_expired_and_revoked_invites_do_nothing(client, admin, login, db):
    invite(client, admin, telegram_id=7004, role="BEEKEEPER")
    db.query(UserInvite).filter_by(telegram_id=7004).update({"expires_at": datetime.now(timezone.utc) - timedelta(days=1)})
    db.commit()
    assert me(login, 7004)["role"] == "VIEWER"

    inv = invite(client, admin, telegram_id=7005, role="BEEKEEPER").json()["invite"]
    r = client.post(f"/api/admin/invites/{inv['id']}/revoke", headers=admin)
    assert r.status_code == 200 and r.json()["status"] == "REVOKED"
    assert client.post(f"/api/admin/invites/{inv['id']}/revoke", headers=admin).status_code == 409
    assert me(login, 7005)["role"] == "VIEWER"


def test_duplicate_pending_refused_until_revoked(client, admin):
    first = invite(client, admin, telegram_id=7006, role="VIEWER").json()["invite"]
    r = invite(client, admin, telegram_id=7006, role="BEEKEEPER")
    assert r.status_code == 409 and "уже есть приглашение" in r.json()["detail"]
    client.post(f"/api/admin/invites/{first['id']}/revoke", headers=admin)
    assert invite(client, admin, telegram_id=7006, role="BEEKEEPER").status_code == 201


def test_expired_invite_does_not_block_a_new_one(client, admin, db):
    invite(client, admin, username="late_guy", role="VIEWER")
    db.query(UserInvite).filter_by(username="late_guy").update({"expires_at": datetime.now(timezone.utc) - timedelta(days=1)})
    db.commit()
    assert invite(client, admin, username="late_guy", role="BEEKEEPER").status_code == 201
    assert db.query(UserInvite).filter_by(username="late_guy", status=InviteStatus.REVOKED).count() == 1


def test_existing_user_role_changed_at_once(client, admin, login):
    me(login, 7007, username="olduser")
    r = invite(client, admin, username="OldUser", role="BEEKEEPER")
    assert r.status_code == 201 and r.json()["kind"] == "updated" and r.json()["user"]["role"] == "BEEKEEPER"
    assert client.get("/api/admin/invites", headers=admin).json() == []
    r = invite(client, admin, telegram_id=1000, role="VIEWER")
    assert r.status_code == 409 and "Свою роль" in r.json()["detail"]


def test_admin_ids_still_win(client, login, as_role):
    admin2 = as_role("ADMIN", 999)
    client.post("/api/admin/invites", json={"telegram_id": 1000, "role": "VIEWER"}, headers=admin2)
    assert me(login, 1000)["role"] == "ADMIN"


@pytest.mark.parametrize("body, fragment", [
    ({"role": "VIEWER"}, "Telegram ID или имя"),
    ({"username": "a b", "role": "VIEWER"}, "латинские буквы"),
    ({"username": "abc", "role": "VIEWER"}, "4–32"),
    ({"telegram_id": -5, "role": "VIEWER"}, ""),
])
def test_invite_validation(client, admin, body, fragment):
    r = client.post("/api/admin/invites", json=body, headers=admin)
    assert r.status_code == 422 and fragment in r.json()["detail"]


def test_admin_only(client, as_role):
    for role in ("BEEKEEPER", "ASSISTANT", "VIEWER"):
        h = as_role(role)
        assert client.get("/api/admin/overview", headers=h).status_code == 403
        assert client.get("/api/admin/audit", headers=h).status_code == 403
        assert client.post("/api/admin/invites", json={"telegram_id": 5, "role": "ADMIN"}, headers=h).status_code == 403
    assert client.get("/api/admin/overview").status_code == 401


def test_last_seen_and_blocking(client, admin, login):
    user = me(login, 7008)
    listed = {u["telegram_id"]: u for u in client.get("/api/users", headers=admin).json()}
    assert listed[7008]["last_seen_at"] is not None
    client.patch(f"/api/users/{user['id']}", json={"is_active": False}, headers=admin)
    from tests.conftest import make_init_data
    r = client.post("/api/auth/telegram", json={"init_data": make_init_data(7008)})
    assert r.status_code == 403 and "отключена" in r.json()["detail"]


def test_overview(client, admin, login):
    apiary = client.post("/api/apiaries", json={"name": "П"}, headers=admin).json()
    client.post("/api/hives", json={"apiary_id": apiary["id"], "hive_number": "1", "family": {}}, headers=admin)
    invite(client, admin, telegram_id=7009, role="VIEWER")
    me(login, 7010)
    r = client.get("/api/admin/overview", headers=admin)
    assert r.status_code == 200, r.text
    o = r.json()
    sys = o["system"]
    assert sys["database_ok"] is True and sys["migration"] and sys["timezone"] and sys["environment"] == "test"
    assert sys["bot_configured"] is True
    assert o["users"]["ADMIN"] == 1 and o["users"]["VIEWER"] == 1 and o["users"]["pending_invites"] == 1
    assert o["users"]["seen_7_days"] == 2
    counts = {c["label"]: c["value"] for c in o["counts"]}
    assert counts["Ульи (на пасеках / в архиве)"] == "1 / 0"
    assert counts["Пасеки (в работе / в архиве)"] == "1 / 0"
    assert {c["section"] for c in o["counts"]} == {"Пасека", "Здоровье", "Мёд и операции", "CRM", "Система"}


def test_activity_log_filters_and_paging(client, admin, login, as_role):
    keeper = as_role("BEEKEEPER", 7011)
    apiary = client.post("/api/apiaries", json={"name": "П"}, headers=keeper).json()
    hive = client.post("/api/hives", json={"apiary_id": apiary["id"], "hive_number": "27"}, headers=keeper).json()
    page = client.get("/api/admin/audit", headers=admin).json()
    assert page["items"][0]["action"] == "created" and page["items"][0]["hive_number"] == "27"
    assert "hive" in page["entity_types"]
    keeper_id = next(u["id"] for u in client.get("/api/users", headers=admin).json() if u["telegram_id"] == 7011)
    mine = client.get("/api/admin/audit", params={"user_id": keeper_id}, headers=admin).json()["items"]
    assert mine and all(e["user_id"] == keeper_id for e in mine)
    hives = client.get("/api/admin/audit", params={"entity_type": "hive"}, headers=admin).json()["items"]
    assert [e["entity_id"] for e in hives] == [hive["id"]]
    total = len(page["items"])
    first = client.get("/api/admin/audit", params={"limit": 1}, headers=admin).json()
    assert len(first["items"]) == 1 and first["next_offset"] == 1
    seen = [first["items"][0]["id"]]
    offset = first["next_offset"]
    while offset is not None:
        p = client.get("/api/admin/audit", params={"limit": 1, "offset": offset}, headers=admin).json()
        seen += [e["id"] for e in p["items"]]
        offset = p["next_offset"]
    assert len(seen) == len(set(seen)) == total  # nothing lost or repeated between pages
