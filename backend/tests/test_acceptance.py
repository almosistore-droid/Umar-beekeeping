"""Stage 10: the ten scenarios the requirements (§38) say must be tested, as one beekeeper would do them.

Each test is a short end-to-end story through the HTTP API with a real Telegram-signed login.
"""
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest

from app.schemas.common import today as app_today
from tests.conftest import make_init_data

TODAY = app_today()


@pytest.fixture
def keeper(login, db):
    from app.models.user import User, UserRole
    headers, body = login(3100)
    user = db.get(User, uuid.UUID(body["user"]["id"]))
    user.role = UserRole.BEEKEEPER
    db.commit()
    return headers


@pytest.fixture
def apiary(client, keeper):
    return client.post("/api/apiaries", json={"name": "Варзоб"}, headers=keeper).json()


def new_hive(client, keeper, apiary, number="27", **extra):
    r = client.post("/api/hives", json={"apiary_id": apiary["id"], "hive_number": number,
                                        "family": {"strength": "STRONG"}, **extra}, headers=keeper)
    assert r.status_code == 201, r.text
    return r.json()


def test_01_create_hive(client, keeper, apiary):
    hive = new_hive(client, keeper, apiary)
    assert hive["hive_number"] == "27" and hive["apiary"]["id"] == apiary["id"]
    assert hive["current_family"]["strength"] == "STRONG"
    # the number is unique per apiary among working hives
    r = client.post("/api/hives", json={"apiary_id": apiary["id"], "hive_number": "27"}, headers=keeper)
    assert r.status_code == 409


def test_02_create_queen(client, keeper):
    r = client.post("/api/queens", json={"queen_code": "M-105", "birth_year": TODAY.year - 1, "breed": "Карника"},
                    headers=keeper)
    assert r.status_code == 201, r.text
    q = r.json()
    assert q["queen_code"] == "M-105" and q["age_label"]  # age is computed, never stored


def test_03_assign_queen_to_hive(client, keeper, apiary):
    hive = new_hive(client, keeper, apiary)
    old = client.post("/api/queens", json={"queen_code": "M-105"}, headers=keeper).json()
    new = client.post("/api/queens", json={"queen_code": "M-205"}, headers=keeper).json()
    client.post(f"/api/hives/{hive['id']}/queen", json={"queen_id": old["id"]}, headers=keeper)
    r = client.post(f"/api/hives/{hive['id']}/queen", json={"queen_id": new["id"], "old_queen_status": "REPLACED"},
                    headers=keeper)
    assert r.status_code in (200, 201), r.text
    assert client.get(f"/api/hives/{hive['id']}", headers=keeper).json()["current_queen"]["queen_code"] == "M-205"
    history = client.get(f"/api/hives/{hive['id']}/queens", headers=keeper).json()
    assert sorted(h["queen_code"] for h in history) == ["M-105", "M-205"]  # history kept
    assert next(h for h in history if h["queen_code"] == "M-105")["removed_at"] is not None


def test_04_create_inspection(client, keeper, apiary):
    hive = new_hive(client, keeper, apiary)
    r = client.post(f"/api/hives/{hive['id']}/inspections",
                    json={"strength": "MEDIUM", "frames_total": 10, "brood_frames": 5, "honey_frames": 3}, headers=keeper)
    assert r.status_code == 201, r.text
    h = r.json()["hive"]
    assert h["current_family"]["strength"] == "MEDIUM" and h["last_inspection_at"] and h["next_inspection_at"]


def test_05_and_06_honey_and_yearly_total(client, keeper, apiary):
    a = new_hive(client, keeper, apiary, "1")
    b = new_hive(client, keeper, apiary, "2")
    for hive, kg in ((a, "12.5"), (a, "8"), (b, "20")):
        r = client.post(f"/api/hives/{hive['id']}/honey", json={"weight_kg": kg, "price_per_kg": "80"}, headers=keeper)
        assert r.status_code == 201, r.text
    honey_a = client.get(f"/api/hives/{a['id']}/honey", headers=keeper).json()
    assert Decimal(honey_a["year_kg"]) == Decimal("20.5")
    assert [x["harvest_number"] for x in honey_a["items"]] == [2, 1]  # numbered per hive and year
    stats = client.get(f"/api/honey/stats?year={TODAY.year}", headers=keeper).json()
    assert Decimal(stats["year_kg"]) == Decimal("40.5")


def test_07_qr_code(client, keeper, apiary, monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "telegram_bot_username", "fayzi_bee_bot")
    hive = new_hive(client, keeper, apiary)
    qr = client.get(f"/api/hives/{hive['id']}/qr", headers=keeper).json()
    assert qr["code"] == f"hive_{hive['id']}" and qr["deep_link"].endswith(f"startapp=hive_{hive['id']}")
    assert qr["content"] == qr["deep_link"] and qr["svg_data_uri"].startswith("data:image/svg+xml")
    # the code is permanent: asking again gives the same one
    assert client.get(f"/api/hives/{hive['id']}/qr", headers=keeper).json()["code"] == qr["code"]


def test_08_open_hive_from_telegram_deep_link(client, keeper, apiary):
    hive = new_hive(client, keeper, apiary)
    # Telegram passes start_param inside the signed initData; the app resolves it to the hive
    r = client.post("/api/auth/telegram", json={"init_data": make_init_data(3100, start_param=f"hive_{hive['id']}")})
    assert r.status_code == 200 and r.json()["start_param"] == f"hive_{hive['id']}"
    resolved = client.get("/api/qr/resolve", params={"code": f"https://t.me/fayzi_bee_bot?startapp=hive_{hive['id']}"},
                          headers=keeper).json()
    assert resolved["status"] == "found" and resolved["hive_id"] == hive["id"]


def test_09_telegram_authorization(client):
    ok = client.post("/api/auth/telegram", json={"init_data": make_init_data(3200)})
    assert ok.status_code == 200 and ok.json()["user"]["role"] == "VIEWER"
    forged = make_init_data(3200).replace("id%22%3A3200", "id%22%3A1000")
    assert client.post("/api/auth/telegram", json={"init_data": forged}).status_code == 401
    wrong_bot = make_init_data(3200, token="1234567:another-bot-token")
    assert client.post("/api/auth/telegram", json={"init_data": wrong_bot}).status_code == 401
    old = make_init_data(3200, auth_date=1_600_000_000)
    assert client.post("/api/auth/telegram", json={"init_data": old}).status_code == 401
    assert client.get("/api/hives").status_code == 401


def test_10_yearly_report(client, keeper, apiary):
    a = new_hive(client, keeper, apiary, "1")
    new_hive(client, keeper, apiary, "2")
    client.post(f"/api/hives/{a['id']}/honey", json={"weight_kg": "30", "price_per_kg": "90"}, headers=keeper)
    rep = client.get(f"/api/reports/yearly/{TODAY.year}", headers=keeper).json()
    assert rep["hives"]["at_end"] == 2 and rep["hives"]["new"] == 2
    assert Decimal(rep["honey"]["total_kg"]) == 30 and rep["honey"]["best_hive"]["hive_number"] == "1"
    for fmt, kind in (("pdf", "application/pdf"), ("xlsx", "spreadsheetml"), ("csv", "text/csv")):
        f = client.get(f"/api/reports/yearly/{TODAY.year}/export", params={"format": fmt}, headers=keeper)
        assert f.status_code == 200 and kind in f.headers["content-type"], fmt
    assert client.get(f"/api/reports/yearly/{TODAY.year + 1}", headers=keeper).status_code == 422


def test_last_week_is_counted_in_the_right_year(client, keeper, apiary):
    """Harvests are counted by the apiary's calendar day (not UTC)."""
    hive = new_hive(client, keeper, apiary)
    day = TODAY - timedelta(days=3)
    client.post(f"/api/hives/{hive['id']}/honey", json={"weight_kg": "5", "harvest_date": str(day)}, headers=keeper)
    stats = client.get(f"/api/honey/stats?year={day.year}", headers=keeper).json()
    assert Decimal(stats["year_kg"]) == 5
