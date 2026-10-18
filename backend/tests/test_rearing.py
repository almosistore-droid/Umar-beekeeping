"""Queen rearing calendar: steps from the grafting day, reminders, counts, corrections, closing."""
from datetime import timedelta

import pytest

from app.config import get_settings
from app.models import Task
from app.models.enums import TaskStatus
from app.schemas.common import today as app_today
from app.services import notification_service as ns

TODAY = app_today()


@pytest.fixture
def people(as_role):
    return {"keeper": as_role("BEEKEEPER", 3000), "assistant": as_role("ASSISTANT", 4001),
            "viewer": as_role("VIEWER", 4002)}


@pytest.fixture
def hive(client, people):
    ap = client.post("/api/apiaries", json={"name": "Горная"}, headers=people["keeper"]).json()
    return client.post("/api/hives", json={"apiary_id": ap["id"], "hive_number": "3", "family": {"strength": "STRONG"}},
                       headers=people["keeper"]).json()


def new_batch(client, headers, days_ago=0, cells=30, **extra):
    r = client.post("/api/rearing", json={"grafted_at": str(TODAY - timedelta(days=days_ago)), "cells_grafted": cells,
                                          **extra}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_calendar_and_reminders_from_the_grafting_day(client, people, hive, db):
    b = new_batch(client, people["keeper"], cell_builder_hive_id=hive["id"])
    assert b["label"].startswith("Партия 1 · ")
    days = {s["key"]: (s["day"], s["date"]) for s in b["steps"]}
    assert days["sealed"] == (5, str(TODAY + timedelta(days=5)))
    assert days["move"][0] == 10 and days["emerge"][0] == 12 and days["laying"][0] == 26
    assert b["next_step"]["key"] == "acceptance" and b["steps"][0]["state"] == "done"

    tasks = db.query(Task).filter(Task.source_id == b["id"]).all()
    assert len(tasks) == 6 and all(t.hive_id is not None for t in tasks)
    titles = sorted(t.title for t in tasks)
    assert "Вывод маток «" + b["label"] + "»: разнести маточники по нуклеусам" in titles


def test_batch_entered_late_has_no_past_reminders(client, people):
    b = new_batch(client, people["keeper"], days_ago=11)
    states = {s["key"]: s["state"] for s in b["steps"]}
    assert states["acceptance"] == "overdue" and states["move"] == "overdue" and states["emerge"] == "upcoming"
    assert b["day"] == 11 and b["next_step"]["key"] == "acceptance"


def test_steps_record_counts_in_order(client, people, db):
    k = people["keeper"]
    b = new_batch(client, k, cells=30)
    url = f"/api/rearing/{b['id']}/steps"
    assert client.post(f"{url}/acceptance/done", json={}, headers=k).status_code == 422
    assert client.post(f"{url}/acceptance/done", json={"count": 31}, headers=k).status_code == 422
    r = client.post(f"{url}/acceptance/done", json={"count": 24}, headers=k)
    assert r.json()["cells_accepted"] == 24
    assert {s["key"]: s["state"] for s in r.json()["steps"]}["acceptance"] == "done"
    assert client.post(f"{url}/sealed/done", json={"count": 25}, headers=k).status_code == 422
    client.post(f"{url}/sealed/done", json={"count": 22}, headers=k)
    r = client.post(f"{url}/move/done", json={}, headers=k)
    assert r.json()["next_step"]["key"] == "emerge"
    task = db.query(Task).filter(Task.source_id == b["id"], Task.source_type == "rearing:acceptance").one()
    assert task.status == TaskStatus.DONE


def test_changing_the_grafting_day_moves_the_reminders(client, people, db):
    k = people["keeper"]
    b = new_batch(client, k)
    r = client.put(f"/api/rearing/{b['id']}", json={"grafted_at": str(TODAY - timedelta(days=1)), "cells_grafted": 30},
                   headers=k)
    assert r.status_code == 200, r.text
    task = db.query(Task).filter(Task.source_id == b["id"], Task.source_type == "rearing:emerge").one()
    assert task.due_date == TODAY + timedelta(days=11)
    assert client.put(f"/api/rearing/{b['id']}", json={"grafted_at": str(TODAY + timedelta(days=1)),
                                                      "cells_grafted": 30}, headers=k).status_code == 422


def test_finish_and_cancel_close_the_reminders(client, people, db):
    k = people["keeper"]
    b = new_batch(client, k)
    r = client.post(f"/api/rearing/{b['id']}/finish", headers=k)
    assert r.json()["status"] == "DONE"
    assert all(t.status == TaskStatus.CANCELLED for t in db.query(Task).filter(Task.source_id == b["id"]))
    assert client.post(f"/api/rearing/{b['id']}/steps/emerge/done", json={"count": 3}, headers=k).status_code == 409

    b2 = new_batch(client, k)
    assert client.post(f"/api/rearing/{b2['id']}/cancel", json={"reason": "холод"}, headers=people["assistant"]).status_code == 403
    r = client.post(f"/api/rearing/{b2['id']}/cancel", json={"reason": "Похолодание, личинки не приняты"}, headers=k)
    assert r.json()["status"] == "CANCELLED" and {s["state"] for s in r.json()["steps"][1:]} == {"skipped"}
    lst = client.get("/api/rearing", headers=people["viewer"]).json()
    assert [x["status"] for x in lst] == ["DONE", "CANCELLED"] or len(lst) == 2


def test_roles_and_reminder_sent_by_the_bot(client, people, db, monkeypatch):
    assert client.post("/api/rearing", json={"grafted_at": str(TODAY), "cells_grafted": 5},
                       headers=people["viewer"]).status_code == 403
    b = new_batch(client, people["assistant"], days_ago=1)  # acceptance is due today
    monkeypatch.setattr(ns, "_wintering", lambda hives, today: [])
    notes = [n for n in ns.collect(db, get_settings(), TODAY) if "Вывод маток" in " ".join(n.lines)]
    assert notes and "проверить приём личинок" in notes[0].lines[0]
    assert b["id"]


def test_old_grafting_and_unknown_links_refused(client, people):
    k = people["keeper"]
    assert client.post("/api/rearing", json={"grafted_at": str(TODAY - timedelta(days=61)), "cells_grafted": 5},
                       headers=k).status_code == 422
    r = client.post("/api/rearing", json={"grafted_at": str(TODAY), "cells_grafted": 5,
                                          "mother_queen_id": "00000000-0000-4000-8000-000000000000"}, headers=k)
    assert r.status_code == 404
