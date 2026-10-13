"""Stage 3: inspections, disease cases, treatments, feedings, reminders, timeline."""
from datetime import date, datetime, timedelta, timezone

import pytest

TODAY = date.today()


@pytest.fixture
def hive(client, beekeeper):
    apiary = client.post("/api/apiaries", json={"name": "Пасека"}, headers=beekeeper).json()
    r = client.post("/api/hives", json={"apiary_id": apiary["id"], "hive_number": "27",
                                        "family": {"strength": "MEDIUM"}}, headers=beekeeper)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def diseases(client, beekeeper):
    return {d["code"]: d for d in client.get("/api/diseases", headers=beekeeper).json()}


def inspect(client, headers, hive_id, **kw):
    body = {"strength": "STRONG", "frames_total": 10, "brood_frames": 6, "honey_frames": 3,
            "pollen_frames": 1, "queen_present": True, "egg_laying": True, **kw}
    return client.post(f"/api/hives/{hive_id}/inspections", json=body, headers=headers)


# ---------- US1 inspections ----------

def test_inspection_updates_hive_state(client, beekeeper, hive):
    r = inspect(client, beekeeper, hive["id"])
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["inspection"]["strength"] == "STRONG"
    assert body["inspection"]["user_name"] == "Иван"
    assert body["warnings"] == []
    h = body["hive"]
    assert h["last_inspection_at"] is not None
    assert h["next_inspection_at"][:10] == (TODAY + timedelta(days=7)).isoformat()
    assert h["current_family"]["strength"] == "STRONG"


def test_inspection_custom_next_date(client, beekeeper, hive):
    nxt = (TODAY + timedelta(days=3)).isoformat()
    h = inspect(client, beekeeper, hive["id"], next_inspection_at=nxt).json()["hive"]
    assert h["next_inspection_at"][:10] == nxt


@pytest.mark.parametrize("override, fragment", [
    ({"frames_total": 5, "brood_frames": 4, "honey_frames": 2, "pollen_frames": 0}, "больше, чем всего рамок"),
    ({"brood_frames": -1}, "не меньше 0"),
    ({"inspected_at": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()}, "будущем"),
    ({"next_inspection_at": (TODAY - timedelta(days=2)).isoformat()}, "раньше этого осмотра"),
    ({"aggressiveness": 9}, "не больше 5"),
])
def test_inspection_validation(client, beekeeper, hive, override, fragment):
    r = inspect(client, beekeeper, hive["id"], **override)
    assert r.status_code == 422
    assert fragment in r.json()["detail"]


def test_queenless_warning_without_changing_queen(client, beekeeper, hive):
    r = inspect(client, beekeeper, hive["id"], queen_present=False, egg_laying=False)
    codes = [w["code"] for w in r.json()["warnings"]]
    assert "possible_queenless" in codes
    assert r.json()["hive"]["status"] == "ACTIVE"


def test_swarming_warning(client, beekeeper, hive):
    r = inspect(client, beekeeper, hive["id"], queen_cells=4)
    assert "swarming_risk" in [w["code"] for w in r.json()["warnings"]]


def test_older_inspection_does_not_move_dates_back(client, beekeeper, hive):
    first = inspect(client, beekeeper, hive["id"]).json()["hive"]
    older = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
    later = inspect(client, beekeeper, hive["id"], inspected_at=older, strength="WEAK").json()["hive"]
    assert later["last_inspection_at"] == first["last_inspection_at"]
    assert later["current_family"]["strength"] == "STRONG"


def test_inspection_refused_for_empty_or_archived_hive(client, beekeeper):
    apiary = client.post("/api/apiaries", json={"name": "P"}, headers=beekeeper).json()
    empty = client.post("/api/hives", json={"apiary_id": apiary["id"], "hive_number": "1"}, headers=beekeeper).json()
    assert inspect(client, beekeeper, empty["id"]).status_code == 409
    sold = client.post("/api/hives", json={"apiary_id": apiary["id"], "hive_number": "2", "family": {}},
                       headers=beekeeper).json()
    client.put(f"/api/hives/{sold['id']}", json={"status": "SOLD"}, headers=beekeeper)
    r = inspect(client, beekeeper, sold["id"])
    assert r.status_code == 409 and "архиве" in r.json()["detail"]


def test_inspection_correction_is_audited_and_recomputes(client, beekeeper, hive):
    ins = inspect(client, beekeeper, hive["id"]).json()["inspection"]
    body = {**{k: ins[k] for k in ("strength", "frames_total", "brood_frames", "honey_frames", "pollen_frames")},
            "strength": "VERY_STRONG", "comment": "опечатка"}
    r = client.put(f"/api/inspections/{ins['id']}", json=body, headers=beekeeper)
    assert r.status_code == 200, r.text
    assert r.json()["hive"]["current_family"]["strength"] == "VERY_STRONG"
    history = client.get(f"/api/hives/{hive['id']}/history", headers=beekeeper).json()
    corr = next(h for h in history if h["action"] == "corrected")
    assert corr["old_value"]["strength"] == "STRONG" and corr["comment"] == "опечатка"


def test_assistant_can_inspect_viewer_cannot(client, hive, as_role):
    assert inspect(client, as_role("ASSISTANT"), hive["id"]).status_code == 201
    viewer = as_role("VIEWER")
    assert inspect(client, viewer, hive["id"]).status_code == 403
    assert client.get(f"/api/hives/{hive['id']}/inspections", headers=viewer).status_code == 200


# ---------- US2 disease cases ----------

def open_case(client, headers, hive_id, disease_id, **kw):
    return client.post(f"/api/hives/{hive_id}/diseases",
                       json={"disease_id": disease_id, "severity": "MODERATE", **kw}, headers=headers)


def test_catalog_seeded(diseases):
    assert {"VARROOSIS", "NOSEMOSIS", "AFB", "EFB", "CHALKBROOD", "VIRAL", "WAX_MOTH", "OTHER"} <= set(diseases)
    assert diseases["AFB"]["is_quarantine"] is True
    assert diseases["VARROOSIS"]["name"] == "Варроатоз"


def test_confirmed_case_makes_hive_sick_and_resolving_restores(client, beekeeper, hive, diseases):
    r = open_case(client, beekeeper, hive["id"], diseases["VARROOSIS"]["id"], status="CONFIRMED")
    assert r.status_code == 201, r.text
    assert r.json()["hive"]["status"] == "SICK"
    case_id = r.json()["case"]["id"]
    r = client.put(f"/api/disease-cases/{case_id}", json={"status": "RESOLVED"}, headers=beekeeper)
    assert r.status_code == 200, r.text
    assert r.json()["case"]["resolved_at"] == TODAY.isoformat()
    assert r.json()["hive"]["status"] == "ACTIVE"


def test_suspected_case_does_not_change_status(client, beekeeper, hive, diseases):
    r = open_case(client, beekeeper, hive["id"], diseases["NOSEMOSIS"]["id"])
    assert r.json()["case"]["status"] == "SUSPECTED"
    assert r.json()["hive"]["status"] == "ACTIVE"


def test_quarantine_disease(client, beekeeper, hive, diseases):
    r = open_case(client, beekeeper, hive["id"], diseases["AFB"]["id"], status="CONFIRMED")
    assert r.json()["hive"]["status"] == "QUARANTINE"


def test_two_cases_resolving_one_keeps_sick(client, beekeeper, hive, diseases):
    a = open_case(client, beekeeper, hive["id"], diseases["VARROOSIS"]["id"], status="CONFIRMED").json()["case"]
    open_case(client, beekeeper, hive["id"], diseases["NOSEMOSIS"]["id"], status="CONFIRMED")
    r = client.put(f"/api/disease-cases/{a['id']}", json={"status": "RESOLVED"}, headers=beekeeper)
    assert r.json()["hive"]["status"] == "SICK"


def test_manual_weak_status_not_overwritten_on_resolve(client, beekeeper, hive, diseases):
    client.put(f"/api/hives/{hive['id']}", json={"status": "WEAK"}, headers=beekeeper)
    case = open_case(client, beekeeper, hive["id"], diseases["VARROOSIS"]["id"]).json()["case"]  # suspected
    r = client.put(f"/api/disease-cases/{case['id']}", json={"status": "RESOLVED"}, headers=beekeeper)
    assert r.json()["hive"]["status"] == "WEAK"


def test_case_transition_rules(client, beekeeper, hive, diseases):
    case = open_case(client, beekeeper, hive["id"], diseases["VARROOSIS"]["id"], status="TREATING").json()["case"]
    r = client.put(f"/api/disease-cases/{case['id']}", json={"status": "SUSPECTED"}, headers=beekeeper)
    assert r.status_code == 409 and "назад" in r.json()["detail"]
    r = client.put(f"/api/disease-cases/{case['id']}",
                   json={"status": "RESOLVED", "resolved_at": (TODAY - timedelta(days=30)).isoformat()},
                   headers=beekeeper)
    assert r.status_code == 422 and "раньше даты обнаружения" in r.json()["detail"]
    client.put(f"/api/disease-cases/{case['id']}", json={"status": "RESOLVED"}, headers=beekeeper)
    r = client.put(f"/api/disease-cases/{case['id']}", json={"status": "TREATING"}, headers=beekeeper)
    assert r.status_code == 409


def test_custom_disease_only_for_managers(client, beekeeper, as_role):
    assert client.post("/api/diseases", json={"name": "Акарапидоз"}, headers=as_role("ASSISTANT")).status_code == 403
    r = client.post("/api/diseases", json={"name": "Акарапидоз"}, headers=beekeeper)
    assert r.status_code == 201
    assert client.post("/api/diseases", json={"name": "акарапидоз"}, headers=beekeeper).status_code == 409


# ---------- US3 treatments ----------

def treat(client, headers, hive_id, **kw):
    return client.post(f"/api/hives/{hive_id}/treatments",
                       json={"medication": "Бипин", "dosage": "1 мл", "method": "Полив", **kw}, headers=headers)


def open_tasks(client, headers, hive_id):
    return client.get("/api/tasks", params={"hive_id": hive_id}, headers=headers).json()


def test_treatment_moves_case_to_treating(client, beekeeper, hive, diseases):
    case = open_case(client, beekeeper, hive["id"], diseases["VARROOSIS"]["id"], status="CONFIRMED").json()["case"]
    r = treat(client, beekeeper, hive["id"], hive_disease_id=case["id"])
    assert r.status_code == 201, r.text
    t = r.json()["treatment"]
    assert t["disease"]["code"] == "VARROOSIS"
    assert t["performed_by_name"] == "Иван"
    cases = client.get(f"/api/hives/{hive['id']}/diseases", headers=beekeeper).json()
    assert cases[0]["status"] == "TREATING"
    assert r.json()["hive"]["status"] == "SICK"


def test_treatment_reminder_lifecycle(client, beekeeper, hive):
    due = (TODAY + timedelta(days=7)).isoformat()
    treat(client, beekeeper, hive["id"], next_treatment_date=due)
    tasks = open_tasks(client, beekeeper, hive["id"])
    assert len(tasks) == 1 and tasks[0]["due_date"] == due and tasks[0]["kind"] == "TREATMENT"
    assert tasks[0]["hive_number"] == "27"
    treat(client, beekeeper, hive["id"])  # follow-up treatment, no further date
    assert open_tasks(client, beekeeper, hive["id"]) == []


def test_treatment_with_other_hive_case_refused(client, beekeeper, hive, diseases):
    apiary_id = hive["apiary"]["id"]
    other = client.post("/api/hives", json={"apiary_id": apiary_id, "hive_number": "28", "family": {}},
                        headers=beekeeper).json()
    case = open_case(client, beekeeper, other["id"], diseases["VARROOSIS"]["id"]).json()["case"]
    r = treat(client, beekeeper, hive["id"], hive_disease_id=case["id"])
    assert r.status_code == 409 and "другом улье" in r.json()["detail"]


def test_treatment_next_date_before_date_refused(client, beekeeper, hive):
    r = treat(client, beekeeper, hive["id"], treated_at=TODAY.isoformat(),
              next_treatment_date=(TODAY - timedelta(days=1)).isoformat())
    assert r.status_code == 422 and "раньше этой" in r.json()["detail"]


def test_treatment_correction_moves_reminder(client, beekeeper, hive):
    t = treat(client, beekeeper, hive["id"], next_treatment_date=(TODAY + timedelta(days=7)).isoformat()).json()
    new_due = (TODAY + timedelta(days=10)).isoformat()
    r = client.put(f"/api/treatments/{t['treatment']['id']}",
                   json={"medication": "Бипин", "next_treatment_date": new_due}, headers=beekeeper)
    assert r.status_code == 200, r.text
    assert [x["due_date"] for x in open_tasks(client, beekeeper, hive["id"])] == [new_due]


# ---------- US4 feedings ----------

def test_feeding_and_reminder(client, beekeeper, hive):
    due = (TODAY + timedelta(days=5)).isoformat()
    r = client.post(f"/api/hives/{hive['id']}/feedings",
                    json={"feed_type": "SUGAR_SYRUP", "quantity": 2, "unit": "L", "reason": "Осенняя",
                          "next_feeding_date": due}, headers=beekeeper)
    assert r.status_code == 201, r.text
    assert r.json()["feeding"]["quantity"] in ("2.00", 2, "2")
    tasks = open_tasks(client, beekeeper, hive["id"])
    assert tasks[0]["kind"] == "FEEDING" and "сахарный сироп" in tasks[0]["title"]


@pytest.mark.parametrize("qty", [0, -1])
def test_feeding_quantity_positive(client, beekeeper, hive, qty):
    r = client.post(f"/api/hives/{hive['id']}/feedings", json={"feed_type": "CANDY", "quantity": qty, "unit": "KG"},
                    headers=beekeeper)
    assert r.status_code == 422


# ---------- US5 timeline, tasks, attention ----------

def test_timeline_merges_everything_in_order(client, beekeeper, hive, diseases):
    queen = client.post("/api/queens", json={"queen_code": "M-105", "hive_id": hive["id"]}, headers=beekeeper)
    assert queen.status_code == 201
    case = open_case(client, beekeeper, hive["id"], diseases["VARROOSIS"]["id"], status="CONFIRMED",
                     detected_at=(TODAY - timedelta(days=20)).isoformat()).json()["case"]
    treat(client, beekeeper, hive["id"], hive_disease_id=case["id"], treated_at=(TODAY - timedelta(days=15)).isoformat())
    client.post(f"/api/hives/{hive['id']}/feedings", json={"feed_type": "CANDY", "quantity": 1.5, "unit": "KG",
                                                           "fed_at": (TODAY - timedelta(days=10)).isoformat()},
                headers=beekeeper)
    inspect(client, beekeeper, hive["id"])

    items = client.get(f"/api/hives/{hive['id']}/timeline", headers=beekeeper).json()
    kinds = [i["kind"] for i in items]
    for k in ("inspection", "feeding", "treatment", "disease_opened", "event"):
        assert k in kinds
    assert items[0]["kind"] in ("inspection", "event")
    times = [i["at"] for i in items]
    assert times == sorted(times, reverse=True)
    insp_item = next(i for i in items if i["kind"] == "inspection")
    assert "Сила: сильная" in insp_item["details"] and insp_item["author"] == "Иван"
    assert any("Рамки: 10" in d for d in insp_item["details"])
    treat_item = next(i for i in items if i["kind"] == "treatment")
    assert treat_item["title"] == "Обработка: Варроатоз"
    feed_item = next(i for i in items if i["kind"] == "feeding")
    assert feed_item["details"][0] == "Канди, 1.5 кг"
    assert any(i["kind"] == "event" and i["action"] == "queen_installed" for i in items)


def test_task_done_and_attention(client, beekeeper, hive, diseases, as_role):
    att = client.get("/api/dashboard/attention", headers=beekeeper).json()
    assert att["needs_inspection"] == 1  # has a family, never inspected
    treat(client, beekeeper, hive["id"], next_treatment_date=TODAY.isoformat())
    open_case(client, beekeeper, hive["id"], diseases["VARROOSIS"]["id"], status="CONFIRMED")
    inspect(client, beekeeper, hive["id"])
    att = client.get("/api/dashboard/attention", headers=beekeeper).json()
    assert att == {"needs_inspection": 0, "open_tasks": 1, "overdue_tasks": 0, "sick": 1}

    task = open_tasks(client, beekeeper, hive["id"])[0]
    assert client.post(f"/api/tasks/{task['id']}/done", headers=as_role("VIEWER")).status_code == 403
    r = client.post(f"/api/tasks/{task['id']}/done", headers=beekeeper)
    assert r.status_code == 200 and r.json()["status"] == "DONE"
    assert client.post(f"/api/tasks/{task['id']}/done", headers=beekeeper).status_code == 409
    assert open_tasks(client, beekeeper, hive["id"]) == []


def test_hive_list_needs_inspection_filter(client, beekeeper, hive):
    params = {"needs_inspection": True}
    assert [h["hive_number"] for h in client.get("/api/hives", params=params, headers=beekeeper).json()["items"]] == ["27"]
    inspect(client, beekeeper, hive["id"])
    assert client.get("/api/hives", params=params, headers=beekeeper).json()["total"] == 0
