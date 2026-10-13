"""«Проверка улья» after a scan: read-only summary of the hive's state and the issues to look at."""
from datetime import date, datetime, timedelta, timezone

import pytest

from app.schemas.common import today as app_today

TODAY = app_today()  # the apiary's calendar day, same clock as the server


@pytest.fixture
def apiary(client, beekeeper):
    return client.post("/api/apiaries", json={"name": "Пасека"}, headers=beekeeper).json()


def hive(client, headers, apiary_id, number="27", family=True, queen=True):
    body = {"apiary_id": apiary_id, "hive_number": number}
    if family:
        body["family"] = {"strength": "MEDIUM"}
    h = client.post("/api/hives", json=body, headers=headers).json()
    if queen and family:
        client.post("/api/queens", json={"queen_code": f"M-{number}", "hive_id": h["id"], "birth_year": TODAY.year},
                    headers=headers)
    return h


def inspect(client, headers, hive_id, **kw):
    body = {"strength": "STRONG", "frames_total": 10, "brood_frames": 6, "honey_frames": 3, "pollen_frames": 1,
            "queen_present": True, "egg_laying": True, "food_level": "NORMAL", **kw}
    r = client.post(f"/api/hives/{hive_id}/inspections", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def check(client, headers, hive_id):
    r = client.get(f"/api/hives/{hive_id}/check", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def codes(body):
    return [i["code"] for i in body["issues"]]


def test_healthy_hive_is_ok(client, beekeeper, apiary):
    h = hive(client, beekeeper, apiary["id"])
    inspect(client, beekeeper, h["id"])
    client.post(f"/api/hives/{h['id']}/honey", json={"weight_kg": 12.5}, headers=beekeeper)
    body = check(client, beekeeper, h["id"])
    assert body["verdict"] == "ok" and body["headline"] == "Всё в порядке" and body["issues"] == []
    assert body["hive_number"] == "27" and body["apiary"]["name"] == "Пасека"
    assert body["strength"] == "STRONG" and body["queen"]["queen_code"] == "M-27"
    li = body["last_inspection"]
    assert li["days_ago"] == 0 and li["brood_frames"] == 6 and li["honey_frames"] == 3 and li["food_level"] == "NORMAL"
    assert li["user_name"]
    assert body["next_inspection_at"][:10] == (TODAY + timedelta(days=7)).isoformat()
    assert float(body["honey_year_kg"]) == 12.5


def test_never_inspected_and_no_queen(client, beekeeper, apiary):
    h = hive(client, beekeeper, apiary["id"], queen=False)
    body = check(client, beekeeper, h["id"])
    assert body["verdict"] == "problem" and body["headline"] == "Есть проблемы"
    assert codes(body) == ["queenless", "never_inspected"]  # problems first
    assert body["last_inspection"] is None


def test_issues_from_last_inspection(client, beekeeper, apiary):
    h = hive(client, beekeeper, apiary["id"])
    inspect(client, beekeeper, h["id"], strength="WEAK", queen_present=False, egg_laying=False, queen_cells=4,
            food_level="LOW", health_status="SUSPICIOUS")
    c = codes(check(client, beekeeper, h["id"]))
    assert {"possible_queenless", "weak", "swarming_risk", "food_low", "health_suspicious"} <= set(c)
    assert c[0] == "possible_queenless"


def test_critical_food_is_a_problem(client, beekeeper, apiary):
    h = hive(client, beekeeper, apiary["id"])
    inspect(client, beekeeper, h["id"], food_level="CRITICAL")
    body = check(client, beekeeper, h["id"])
    assert body["verdict"] == "problem" and codes(body) == ["food_critical"]


def test_overdue_inspection_and_reminder(client, beekeeper, apiary):
    h = hive(client, beekeeper, apiary["id"])
    old = datetime.now(timezone.utc) - timedelta(days=12)
    inspect(client, beekeeper, h["id"], inspected_at=old.isoformat())
    client.post(f"/api/hives/{h['id']}/feedings",
                json={"feed_type": "SUGAR_SYRUP", "quantity": 2, "unit": "L",
                      "fed_at": (TODAY - timedelta(days=8)).isoformat(),
                      "next_feeding_date": (TODAY - timedelta(days=1)).isoformat()}, headers=beekeeper)
    body = check(client, beekeeper, h["id"])
    assert body["verdict"] == "attention" and body["headline"] == "Требует внимания"
    msgs = {i["code"]: i["message"] for i in body["issues"]}
    assert msgs["inspection_overdue"] == "Осмотр просрочен на 5 дней"
    assert msgs["task_overdue"].startswith("Просрочено:")
    assert body["last_inspection"]["days_ago"] == 12
    assert body["open_tasks"][0]["overdue"] is True


def test_diseases(client, beekeeper, apiary):
    h = hive(client, beekeeper, apiary["id"])
    inspect(client, beekeeper, h["id"])
    diseases = {d["code"]: d for d in client.get("/api/diseases", headers=beekeeper).json()}
    client.post(f"/api/hives/{h['id']}/diseases", json={"disease_id": diseases["NOSEMOSIS"]["id"]}, headers=beekeeper)
    body = check(client, beekeeper, h["id"])
    assert codes(body) == ["disease_suspected"] and body["open_cases"][0]["status"] == "подозрение"
    client.post(f"/api/hives/{h['id']}/diseases", json={"disease_id": diseases["AFB"]["id"], "status": "CONFIRMED"},
                headers=beekeeper)
    body = check(client, beekeeper, h["id"])
    assert body["status"] == "QUARANTINE" and codes(body)[0] == "quarantine" and len(body["open_cases"]) == 2


def test_empty_and_archived(client, beekeeper, apiary):
    empty = hive(client, beekeeper, apiary["id"], "1", family=False)
    assert codes(check(client, beekeeper, empty["id"])) == ["no_family"]
    sold = hive(client, beekeeper, apiary["id"], "2")
    client.put(f"/api/hives/{sold['id']}", json={"status": "SOLD"}, headers=beekeeper)
    body = check(client, beekeeper, sold["id"])
    assert body["is_archived"] is True and codes(body) == ["archived"]


def test_viewer_can_check_and_unknown_hive(client, beekeeper, apiary, as_role):
    h = hive(client, beekeeper, apiary["id"])
    assert client.get(f"/api/hives/{h['id']}/check", headers=as_role("VIEWER")).status_code == 200
    r = client.get("/api/hives/00000000-0000-4000-8000-000000000000/check", headers=beekeeper)
    assert r.status_code == 404 and r.json()["detail"] == "Улей не найден"
    assert client.get(f"/api/hives/{h['id']}/check").status_code == 401


def test_check_writes_nothing(client, beekeeper, apiary):
    h = hive(client, beekeeper, apiary["id"])
    before = client.get(f"/api/hives/{h['id']}/history", headers=beekeeper).json()
    check(client, beekeeper, h["id"])
    assert client.get(f"/api/hives/{h['id']}/history", headers=beekeeper).json() == before
    assert isinstance(date.fromisoformat(TODAY.isoformat()), date)
