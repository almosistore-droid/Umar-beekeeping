"""Records saved on the phone without internet are sent later, possibly twice: one client_uid = one record."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models import Feeding, Inspection, Treatment


@pytest.fixture
def setup(client, beekeeper):
    ap = client.post("/api/apiaries", json={"name": "Горная"}, headers=beekeeper).json()
    make = lambda n: client.post("/api/hives", json={"apiary_id": ap["id"], "hive_number": n,  # noqa: E731
                                                     "family": {"strength": "MEDIUM"}}, headers=beekeeper).json()
    return make("1"), make("2")


def test_feeding_sent_twice_is_saved_once(client, beekeeper, setup, db):
    hive, _ = setup
    uid = str(uuid.uuid4())
    body = {"feed_type": "SUGAR_SYRUP", "quantity": "2", "unit": "L", "client_uid": uid}
    first = client.post(f"/api/hives/{hive['id']}/feedings", json=body, headers=beekeeper)
    again = client.post(f"/api/hives/{hive['id']}/feedings", json=body, headers=beekeeper)
    assert first.status_code == again.status_code == 201
    assert first.json()["feeding"]["id"] == again.json()["feeding"]["id"]
    assert db.query(Feeding).count() == 1
    sugar = next(i for i in client.get("/api/stock", headers=beekeeper).json()["items"] if i["code"] == "sugar")
    assert float(sugar["quantity"]) == -1.26  # written off once


def test_inspection_with_past_time_and_resend(client, beekeeper, setup, db):
    hive, _ = setup
    uid = str(uuid.uuid4())
    when = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
    body = {"strength": "STRONG", "frames_total": 10, "inspected_at": when, "client_uid": uid}
    r1 = client.post(f"/api/hives/{hive['id']}/inspections", json=body, headers=beekeeper)
    r2 = client.post(f"/api/hives/{hive['id']}/inspections", json=body, headers=beekeeper)
    assert r1.status_code == 201 and r2.status_code == 201
    assert r2.json()["warnings"] == []
    assert db.query(Inspection).count() == 1


def test_same_uid_for_another_hive_is_refused(client, beekeeper, setup):
    a, b = setup
    uid = str(uuid.uuid4())
    body = {"medication": "Бипин", "client_uid": uid}
    assert client.post(f"/api/hives/{a['id']}/treatments", json=body, headers=beekeeper).status_code == 201
    r = client.post(f"/api/hives/{b['id']}/treatments", json=body, headers=beekeeper)
    assert r.status_code == 409


def test_resend_after_the_hive_was_archived_returns_the_saved_record(client, beekeeper, setup, db):
    hive, _ = setup
    uid = str(uuid.uuid4())
    body = {"medication": "Бипин", "client_uid": uid}
    client.post(f"/api/hives/{hive['id']}/treatments", json=body, headers=beekeeper)
    client.put(f"/api/hives/{hive['id']}", json={"status": "SOLD"}, headers=beekeeper)
    r = client.post(f"/api/hives/{hive['id']}/treatments", json=body, headers=beekeeper)
    assert r.status_code == 201
    assert db.query(Treatment).count() == 1
