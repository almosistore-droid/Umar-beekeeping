"""Stage 2: apiaries, hives, families, queens, history and permissions."""
from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from app.models import AuditLog, BeeFamily, Hive, Queen, QueenAssignment

TODAY = date.today()


@pytest.fixture
def apiary(client, beekeeper):
    r = client.post("/api/apiaries", json={"name": "Пасека №1", "address": "Варзоб"}, headers=beekeeper)
    assert r.status_code == 201, r.text
    return r.json()


def make_hive(client, headers, apiary_id, number="27", **extra):
    body = {"apiary_id": apiary_id, "hive_number": number, "hive_type": "DADANT",
            "family": {"strength": "STRONG", "origin": "PURCHASED"}, **extra}
    r = client.post("/api/hives", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def make_queen(client, headers, code="M-105", **extra):
    body = {"queen_code": code, "birth_date": "2024-06-15", "breed": "Карника", **extra}
    r = client.post("/api/queens", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ---------- apiaries ----------

def test_create_and_list_apiaries(client, beekeeper, apiary):
    client.post("/api/apiaries", json={"name": "Горная"}, headers=beekeeper)
    r = client.get("/api/apiaries", headers=beekeeper)
    assert [a["name"] for a in r.json()] == ["Горная", "Пасека №1"]


def test_apiary_validation_messages_are_russian(client, beekeeper):
    r = client.post("/api/apiaries", json={"name": "   ", "latitude": 120}, headers=beekeeper)
    assert r.status_code == 422
    messages = " ".join(e["message"] for e in r.json()["errors"])
    assert "Название пасеки не может быть пустым" in messages
    assert "Широта" in messages


def test_cannot_archive_apiary_with_active_hives(client, beekeeper, apiary):
    make_hive(client, beekeeper, apiary["id"])
    r = client.put(f"/api/apiaries/{apiary['id']}", json={"is_archived": True}, headers=beekeeper)
    assert r.status_code == 409


# ---------- hives ----------

def test_create_hive_with_family(client, beekeeper, apiary, db):
    hive = make_hive(client, beekeeper, apiary["id"], "№27")
    assert hive["hive_number"] == "27"
    assert hive["status"] == "ACTIVE"
    assert hive["current_family"]["strength"] == "STRONG"
    assert hive["current_family"]["start_date"] == TODAY.isoformat()
    assert hive["version"] == 1
    assert hive["apiary"]["name"] == "Пасека №1"
    assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "created")) >= 2


def test_create_empty_hive(client, beekeeper, apiary):
    r = client.post("/api/hives", json={"apiary_id": apiary["id"], "hive_number": "1"}, headers=beekeeper)
    assert r.status_code == 201
    assert r.json()["status"] == "EMPTY"
    assert r.json()["current_family"] is None


def test_populated_status_requires_family(client, beekeeper, apiary):
    r = client.post("/api/hives", json={"apiary_id": apiary["id"], "hive_number": "1", "status": "STRONG"},
                    headers=beekeeper)
    assert r.status_code == 422


def test_duplicate_number_in_same_apiary_rejected(client, beekeeper, apiary):
    make_hive(client, beekeeper, apiary["id"], "5")
    r = client.post("/api/hives", json={"apiary_id": apiary["id"], "hive_number": "5"}, headers=beekeeper)
    assert r.status_code == 409
    assert "№5" in r.json()["detail"]


def test_same_number_allowed_in_other_apiary(client, beekeeper, apiary):
    other = client.post("/api/apiaries", json={"name": "Вторая"}, headers=beekeeper).json()
    make_hive(client, beekeeper, apiary["id"], "5")
    make_hive(client, beekeeper, other["id"], "5")


def test_number_reusable_after_hive_is_archived(client, beekeeper, apiary):
    hive = make_hive(client, beekeeper, apiary["id"], "5")
    r = client.put(f"/api/hives/{hive['id']}", json={"status": "LOST", "comment": "Зимой погибла"}, headers=beekeeper)
    assert r.status_code == 200, r.text
    assert r.json()["is_archived"] is True
    make_hive(client, beekeeper, apiary["id"], "5")


def test_future_dates_rejected(client, beekeeper, apiary):
    future = (TODAY + timedelta(days=10)).isoformat()
    r = client.post("/api/hives", json={"apiary_id": apiary["id"], "hive_number": "1", "installation_date": future},
                    headers=beekeeper)
    assert r.status_code == 422
    assert "будущем" in r.json()["detail"]


def test_unknown_hive_is_404(client, beekeeper):
    r = client.get("/api/hives/550e8400-e29b-41d4-a716-446655440000", headers=beekeeper)
    assert r.status_code == 404
    assert r.json()["detail"] == "Улей не найден"


def test_hive_for_unknown_apiary_is_404(client, beekeeper):
    r = client.post("/api/hives", json={"apiary_id": "550e8400-e29b-41d4-a716-446655440000", "hive_number": "1"},
                    headers=beekeeper)
    assert r.status_code == 404


def test_number_change_keeps_uuid_and_is_audited(client, beekeeper, apiary):
    hive = make_hive(client, beekeeper, apiary["id"], "27")
    r = client.put(f"/api/hives/{hive['id']}", json={"hive_number": "127", "version": 1}, headers=beekeeper)
    assert r.status_code == 200
    assert r.json()["id"] == hive["id"]
    assert r.json()["version"] == 2
    history = client.get(f"/api/hives/{hive['id']}/history", headers=beekeeper).json()
    change = next(h for h in history if h["action"] == "number_changed")
    assert change["old_value"] == {"hive_number": "27"}
    assert change["new_value"] == {"hive_number": "127"}
    assert change["user_name"] == "Иван"


def test_stale_version_conflict(client, beekeeper, apiary):
    hive = make_hive(client, beekeeper, apiary["id"])
    client.put(f"/api/hives/{hive['id']}", json={"notes": "a", "version": 1}, headers=beekeeper)
    r = client.put(f"/api/hives/{hive['id']}", json={"notes": "b", "version": 1}, headers=beekeeper)
    assert r.status_code == 409


def test_list_and_search_hives(client, beekeeper, apiary):
    for n in ["10", "2", "1"]:
        make_hive(client, beekeeper, apiary["id"], n)
    r = client.get("/api/hives", headers=beekeeper).json()
    assert [h["hive_number"] for h in r["items"]] == ["1", "2", "10"]
    assert r["total"] == 3
    r = client.get("/api/hives", params={"q": "№10"}, headers=beekeeper).json()
    assert [h["hive_number"] for h in r["items"]] == ["10"]


def test_archived_hidden_by_default(client, beekeeper, apiary):
    hive = make_hive(client, beekeeper, apiary["id"])
    client.put(f"/api/hives/{hive['id']}", json={"status": "SOLD"}, headers=beekeeper)
    assert client.get("/api/hives", headers=beekeeper).json()["total"] == 0
    assert client.get("/api/hives", params={"include_archived": True}, headers=beekeeper).json()["total"] == 1


def test_archived_hive_cannot_be_changed(client, beekeeper, apiary):
    hive = make_hive(client, beekeeper, apiary["id"])
    client.put(f"/api/hives/{hive['id']}", json={"status": "SOLD"}, headers=beekeeper)
    r = client.put(f"/api/hives/{hive['id']}", json={"status": "ACTIVE"}, headers=beekeeper)
    assert r.status_code == 409
    r = client.put(f"/api/hives/{hive['id']}", json={"notes": "Продан соседу"}, headers=beekeeper)
    assert r.status_code == 200


# ---------- queens ----------

def test_create_queen_computes_age(client, beekeeper):
    q = make_queen(client, beekeeper)
    assert q["queen_code"] == "M-105"
    assert q["birth_year"] == 2024
    assert q["marking_color"] == "GREEN"  # 2024 -> green
    assert q["age_months"] > 0
    assert q["age_label"]
    assert q["current_hive"] is None


def test_queen_code_unique(client, beekeeper):
    make_queen(client, beekeeper, "M-1")
    r = client.post("/api/queens", json={"queen_code": "m-1"}, headers=beekeeper)
    assert r.status_code == 409


@pytest.mark.parametrize(
    "body, fragment",
    [
        ({"birth_date": (TODAY + timedelta(days=30)).isoformat()}, "будущем"),
        ({"birth_year": TODAY.year + 1}, "будущем"),
        ({"birth_date": "2024-06-15", "birth_year": 2023}, "не совпадает"),
        ({"egg_laying_quality": 9}, "Яйценоскость"),
    ],
)
def test_invalid_birth_data_rejected(client, beekeeper, body, fragment):
    r = client.post("/api/queens", json={"queen_code": "X", **body}, headers=beekeeper)
    assert r.status_code == 422
    assert fragment in r.json()["detail"]


def test_assign_queen_to_hive(client, beekeeper, apiary, db):
    hive = make_hive(client, beekeeper, apiary["id"])
    queen = make_queen(client, beekeeper)
    r = client.post(f"/api/hives/{hive['id']}/queen", json={"queen_id": queen["id"]}, headers=beekeeper)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["current_queen"]["queen_code"] == "M-105"
    assert body["current_queen"]["age_label"]
    q = client.get(f"/api/queens/{queen['id']}", headers=beekeeper).json()
    assert q["current_hive"]["hive_number"] == "27"
    assert q["installed_at"] == TODAY.isoformat()


def test_replace_queen_keeps_history(client, beekeeper, apiary, db):
    hive = make_hive(client, beekeeper, apiary["id"])
    old = make_queen(client, beekeeper, "M-105")
    new = make_queen(client, beekeeper, "M-205", birth_date="2026-05-01")
    client.post(f"/api/hives/{hive['id']}/queen", json={"queen_id": old["id"]}, headers=beekeeper)
    r = client.post(f"/api/hives/{hive['id']}/queen",
                    json={"queen_id": new["id"], "previous_queen_status": "REPLACED", "removal_reason": "Старая"},
                    headers=beekeeper)
    assert r.status_code == 200, r.text
    assert r.json()["current_queen"]["queen_code"] == "M-205"

    old_q = client.get(f"/api/queens/{old['id']}", headers=beekeeper).json()
    assert old_q["status"] == "REPLACED"
    assert old_q["current_hive"] is None
    assert old_q["removed_at"] == TODAY.isoformat()

    periods = client.get(f"/api/hives/{hive['id']}/queens", headers=beekeeper).json()
    assert {p["queen_code"] for p in periods} == {"M-105", "M-205"}
    assert next(p for p in periods if p["queen_code"] == "M-105")["removed_at"] == TODAY.isoformat()

    # Audit entry in the spec's "M-105 → M-205" form
    history = client.get(f"/api/hives/{hive['id']}/history", headers=beekeeper).json()
    replaced = next(h for h in history if h["action"] == "queen_replaced")
    assert replaced["old_value"]["queen_code"] == "M-105"
    assert replaced["new_value"]["queen_code"] == "M-205"


def test_only_one_active_queen_per_hive_in_db(client, beekeeper, apiary, db):
    hive = make_hive(client, beekeeper, apiary["id"])
    a = make_queen(client, beekeeper, "A")
    b = make_queen(client, beekeeper, "B")
    client.post(f"/api/hives/{hive['id']}/queen", json={"queen_id": a["id"]}, headers=beekeeper)
    client.post(f"/api/hives/{hive['id']}/queen", json={"queen_id": b["id"]}, headers=beekeeper)
    in_hive = db.scalars(select(Queen).where(Queen.current_hive_id == hive["id"])).all()
    assert [q.queen_code for q in in_hive] == ["B"]


def test_db_constraint_blocks_second_queen(db, client, beekeeper, apiary):
    from sqlalchemy.exc import IntegrityError
    hive = make_hive(client, beekeeper, apiary["id"])
    a = make_queen(client, beekeeper, "A")
    client.post(f"/api/hives/{hive['id']}/queen", json={"queen_id": a["id"]}, headers=beekeeper)
    db.add(Queen(queen_code="ROGUE", current_hive_id=hive["id"]))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_move_queen_between_hives(client, beekeeper, apiary):
    h1 = make_hive(client, beekeeper, apiary["id"], "1")
    h2 = make_hive(client, beekeeper, apiary["id"], "2")
    q = make_queen(client, beekeeper)
    client.post(f"/api/hives/{h1['id']}/queen", json={"queen_id": q["id"]}, headers=beekeeper)
    r = client.post(f"/api/hives/{h2['id']}/queen", json={"queen_id": q["id"]}, headers=beekeeper)
    assert r.status_code == 200, r.text
    h1_now = client.get(f"/api/hives/{h1['id']}", headers=beekeeper).json()
    assert h1_now["current_queen"] is None
    assert h1_now["status"] == "QUEENLESS"
    q_now = client.get(f"/api/queens/{q['id']}", headers=beekeeper).json()
    assert q_now["status"] == "ACTIVE"
    assert q_now["current_hive"]["hive_number"] == "2"
    assert len(client.get(f"/api/queens/{q['id']}/history", headers=beekeeper).json()) == 2


def test_remove_queen_marks_hive_queenless(client, beekeeper, apiary):
    hive = make_hive(client, beekeeper, apiary["id"])
    q = make_queen(client, beekeeper)
    client.post(f"/api/hives/{hive['id']}/queen", json={"queen_id": q["id"]}, headers=beekeeper)
    r = client.post(f"/api/hives/{hive['id']}/queen/remove", json={"status": "DEAD", "reason": "Не найдена"},
                    headers=beekeeper)
    assert r.status_code == 200
    assert r.json()["status"] == "QUEENLESS"
    assert client.get(f"/api/queens/{q['id']}", headers=beekeeper).json()["status"] == "DEAD"
    # Dead queen cannot be re-installed
    r = client.post(f"/api/hives/{hive['id']}/queen", json={"queen_id": q["id"]}, headers=beekeeper)
    assert r.status_code == 409


def test_queen_into_empty_hive_rejected(client, beekeeper, apiary):
    r = client.post("/api/hives", json={"apiary_id": apiary["id"], "hive_number": "1"}, headers=beekeeper)
    q = make_queen(client, beekeeper)
    r = client.post(f"/api/hives/{r.json()['id']}/queen", json={"queen_id": q["id"]}, headers=beekeeper)
    assert r.status_code == 409
    assert "семьи" in r.json()["detail"]


def test_install_before_birth_rejected(client, beekeeper, apiary):
    hive = make_hive(client, beekeeper, apiary["id"])
    q = make_queen(client, beekeeper, birth_date="2025-05-01")
    r = client.post(f"/api/hives/{hive['id']}/queen", json={"queen_id": q["id"], "installed_at": "2025-01-01"},
                    headers=beekeeper)
    assert r.status_code == 422


def test_create_queen_directly_into_hive(client, beekeeper, apiary):
    hive = make_hive(client, beekeeper, apiary["id"])
    make_queen(client, beekeeper, "M-7", hive_id=hive["id"])
    assert client.get(f"/api/hives/{hive['id']}", headers=beekeeper).json()["current_queen"]["queen_code"] == "M-7"


def test_selling_hive_retires_family_and_queen(client, beekeeper, apiary, db):
    hive = make_hive(client, beekeeper, apiary["id"])
    q = make_queen(client, beekeeper, hive_id=hive["id"])
    r = client.put(f"/api/hives/{hive['id']}", json={"status": "SOLD"}, headers=beekeeper)
    assert r.json()["current_family"] is None and r.json()["current_queen"] is None
    assert client.get(f"/api/queens/{q['id']}", headers=beekeeper).json()["status"] == "SOLD"
    families = client.get(f"/api/hives/{hive['id']}/families", headers=beekeeper).json()
    assert families[0]["status"] == "SOLD"
    # Hive row still exists
    assert db.get(Hive, __import__("uuid").UUID(hive["id"])) is not None


# ---------- families ----------

def test_replace_family_keeps_history(client, beekeeper, apiary):
    hive = make_hive(client, beekeeper, apiary["id"])
    q = make_queen(client, beekeeper, hive_id=hive["id"])
    r = client.post(f"/api/hives/{hive['id']}/families",
                    json={"strength": "WEAK", "origin": "SWARM", "previous_status": "DEAD", "end_reason": "Варроа"},
                    headers=beekeeper)
    assert r.status_code == 201, r.text
    assert r.json()["current_family"]["strength"] == "WEAK"
    assert r.json()["current_queen"] is None
    families = client.get(f"/api/hives/{hive['id']}/families", headers=beekeeper).json()
    assert sorted(f["status"] for f in families) == ["ACTIVE", "DEAD"]
    assert client.get(f"/api/queens/{q['id']}", headers=beekeeper).json()["status"] == "REPLACED"


def test_end_family_empties_hive(client, beekeeper, apiary):
    hive = make_hive(client, beekeeper, apiary["id"])
    r = client.post(f"/api/hives/{hive['id']}/family/end", json={"status": "ABSCONDED", "end_reason": "Слёт"},
                    headers=beekeeper)
    assert r.status_code == 200
    assert r.json()["status"] == "EMPTY"
    assert r.json()["current_family"] is None
    # Settle a new family afterwards
    r = client.post(f"/api/hives/{hive['id']}/families", json={"strength": "MEDIUM", "origin": "PACKAGE"},
                    headers=beekeeper)
    assert r.json()["status"] == "ACTIVE"
    assert len(client.get(f"/api/hives/{hive['id']}/families", headers=beekeeper).json()) == 2


def test_family_strength_update_audited(client, beekeeper, apiary, as_role):
    hive = make_hive(client, beekeeper, apiary["id"])
    assistant = as_role("ASSISTANT")
    r = client.patch(f"/api/hives/{hive['id']}/family", json={"strength": "VERY_STRONG"}, headers=assistant)
    assert r.status_code == 200
    assert r.json()["current_family"]["strength"] == "VERY_STRONG"
    history = client.get(f"/api/hives/{hive['id']}/history", headers=beekeeper).json()
    entry = next(h for h in history if h["entity_type"] == "bee_family")
    assert entry["old_value"] == {"strength": "STRONG"}


def test_only_one_active_family_in_db(client, beekeeper, apiary, db):
    from sqlalchemy.exc import IntegrityError
    hive = make_hive(client, beekeeper, apiary["id"])
    db.add(BeeFamily(hive_id=hive["id"], start_date=TODAY))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


# ---------- permissions ----------

def test_viewer_can_read_but_not_write(client, beekeeper, apiary, as_role):
    viewer = as_role("VIEWER")
    hive = make_hive(client, beekeeper, apiary["id"])
    assert client.get(f"/api/hives/{hive['id']}", headers=viewer).status_code == 200
    assert client.get("/api/queens", headers=viewer).status_code == 200
    assert client.post("/api/apiaries", json={"name": "X"}, headers=viewer).status_code == 403
    assert client.put(f"/api/hives/{hive['id']}", json={"notes": "x"}, headers=viewer).status_code == 403
    assert client.post("/api/queens", json={"queen_code": "X"}, headers=viewer).status_code == 403
    assert client.patch(f"/api/hives/{hive['id']}/family", json={"strength": "WEAK"}, headers=viewer).status_code == 403


def test_assistant_cannot_manage_structure(client, beekeeper, apiary, as_role):
    assistant = as_role("ASSISTANT")
    assert client.post("/api/hives", json={"apiary_id": apiary["id"], "hive_number": "9"},
                       headers=assistant).status_code == 403


def test_anonymous_rejected(client):
    assert client.get("/api/hives").status_code == 401
    assert client.get("/api/apiaries").status_code == 401


# ---------- users ----------

def test_admin_manages_roles(client, login, as_role):
    admin, _ = login(1000)
    _, viewer_body = login(2000)
    r = client.patch(f"/api/users/{viewer_body['user']['id']}", json={"role": "ASSISTANT"}, headers=admin)
    assert r.status_code == 200
    assert r.json()["role"] == "ASSISTANT"
    assert len(client.get("/api/users", headers=admin).json()) == 2


def test_admin_cannot_demote_self(client, login):
    admin, body = login(1000)
    r = client.patch(f"/api/users/{body['user']['id']}", json={"role": "VIEWER"}, headers=admin)
    assert r.status_code == 409


def test_non_admin_cannot_list_users(client, beekeeper):
    assert client.get("/api/users", headers=beekeeper).status_code == 403


def test_queen_assignment_rows(db, client, beekeeper, apiary):
    hive = make_hive(client, beekeeper, apiary["id"])
    make_queen(client, beekeeper, hive_id=hive["id"])
    rows = db.scalars(select(QueenAssignment)).unique().all()
    assert len(rows) == 1 and rows[0].removed_at is None


def test_filter_by_strength(client, beekeeper, apiary):
    make_hive(client, beekeeper, apiary["id"], "1")  # STRONG
    r = client.post("/api/hives", json={"apiary_id": apiary["id"], "hive_number": "2",
                                        "family": {"strength": "WEAK"}}, headers=beekeeper)
    assert r.status_code == 201
    res = client.get("/api/hives", params=[("strength", "WEAK"), ("strength", "VERY_WEAK")], headers=beekeeper).json()
    assert [h["hive_number"] for h in res["items"]] == ["2"]
