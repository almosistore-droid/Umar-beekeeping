"""Stage 4: honey, products, movement, swarm, split, merge, wintering."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

TODAY = date.today()
Y = TODAY.year


@pytest.fixture
def apiary(client, beekeeper):
    return client.post("/api/apiaries", json={"name": "Пасека №1"}, headers=beekeeper).json()


@pytest.fixture
def apiary2(client, beekeeper):
    return client.post("/api/apiaries", json={"name": "Горная"}, headers=beekeeper).json()


def hive(client, headers, apiary_id, number, family=True, **kw):
    body = {"apiary_id": apiary_id, "hive_number": number, **kw}
    if family:
        body["family"] = {"strength": kw.pop("strength", "MEDIUM")}
    r = client.post("/api/hives", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def queen(client, headers, code, hive_id=None):
    body = {"queen_code": code, **({"hive_id": hive_id} if hive_id else {})}
    r = client.post("/api/queens", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def get(client, headers, hive_id):
    return client.get(f"/api/hives/{hive_id}", headers=headers).json()


# ---------- US1 honey ----------

def harvest(client, headers, hive_id, **kw):
    return client.post(f"/api/hives/{hive_id}/honey", json={"weight_kg": 10, **kw}, headers=headers)


def test_harvest_value_and_numbering(client, beekeeper, apiary):
    h = hive(client, beekeeper, apiary["id"], "1")
    r = harvest(client, beekeeper, h["id"], weight_kg="12.5", price_per_kg=80, honey_type="Разнотравье", frames_count=6)
    assert r.status_code == 201, r.text
    first = r.json()
    assert Decimal(first["total_value"]) == Decimal("1000.00")
    assert first["harvest_number"] == 1 and first["harvest_year"] == Y
    assert harvest(client, beekeeper, h["id"]).json()["harvest_number"] == 2
    last_year = harvest(client, beekeeper, h["id"], harvest_date=date(Y - 1, 8, 1).isoformat()).json()
    assert last_year["harvest_number"] == 1 and last_year["total_value"] is None


@pytest.mark.parametrize("body, fragment", [
    ({"weight_kg": 0}, "Вес"), ({"weight_kg": -3}, "Вес"),
    ({"weight_kg": 5, "price_per_kg": -1}, "не меньше 0"), ({"weight_kg": 5, "frames_count": -1}, "не меньше 0"),
    ({"weight_kg": 5, "harvest_date": (TODAY + timedelta(days=5)).isoformat()}, "будущем"),
])
def test_harvest_validation(client, beekeeper, apiary, body, fragment):
    h = hive(client, beekeeper, apiary["id"], "1")
    r = client.post(f"/api/hives/{h['id']}/honey", json=body, headers=beekeeper)
    assert r.status_code == 422 and fragment in r.json()["detail"]


def test_honey_stats(client, beekeeper, apiary, apiary2):
    a = hive(client, beekeeper, apiary["id"], "1")
    b = hive(client, beekeeper, apiary2["id"], "2")
    harvest(client, beekeeper, a["id"], weight_kg=20, price_per_kg=50, harvest_date=date(Y, 5, 10).isoformat())
    harvest(client, beekeeper, a["id"], weight_kg=15, harvest_date=date(Y, 8, 2).isoformat())
    harvest(client, beekeeper, b["id"], weight_kg=10, price_per_kg=60, harvest_date=date(Y, 8, 20).isoformat())
    harvest(client, beekeeper, b["id"], weight_kg=7, harvest_date=date(Y - 1, 7, 1).isoformat())

    s = client.get("/api/honey/stats", params={"year": Y}, headers=beekeeper).json()
    assert Decimal(s["year_kg"]) == 45 and Decimal(s["season_kg"]) == 45
    assert Decimal(s["all_time_kg"]) == 52
    assert Decimal(s["year_value"]) == 1600
    assert s["producing_hives"] == 2 and Decimal(s["avg_per_hive_kg"]) == Decimal("22.50")
    assert s["best_hive"]["hive_number"] == "1" and Decimal(s["best_hive"]["kg"]) == 35
    assert Decimal(s["by_month"][4]) == 20 and Decimal(s["by_month"][7]) == 25
    per_apiary = client.get("/api/honey/stats", params={"year": Y, "apiary_id": apiary2["id"]}, headers=beekeeper).json()
    assert Decimal(per_apiary["year_kg"]) == 10

    hh = client.get(f"/api/hives/{a['id']}/honey", headers=beekeeper).json()
    assert Decimal(hh["year_kg"]) == 35 and Decimal(hh["year_value"]) == 1000 and len(hh["items"]) == 2


def test_harvest_correction_audited(client, beekeeper, apiary):
    h = hive(client, beekeeper, apiary["id"], "1")
    hv = harvest(client, beekeeper, h["id"], weight_kg=10, price_per_kg=10).json()
    r = client.put(f"/api/honey/{hv['id']}", json={"weight_kg": 11, "price_per_kg": 10}, headers=beekeeper)
    assert Decimal(r.json()["total_value"]) == 110
    assert any(e["action"] == "corrected" for e in client.get(f"/api/hives/{h['id']}/history", headers=beekeeper).json())


def test_viewer_cannot_harvest(client, beekeeper, apiary, as_role):
    h = hive(client, beekeeper, apiary["id"], "1")
    assert harvest(client, as_role("VIEWER"), h["id"]).status_code == 403
    assert harvest(client, as_role("ASSISTANT"), h["id"]).status_code == 201


# ---------- US5 products ----------

def test_products(client, beekeeper, apiary):
    h = hive(client, beekeeper, apiary["id"], "1")
    r = client.post("/api/products", json={"product_type": "WAX", "quantity": "1.2", "unit": "KG",
                                           "price_per_unit": 150, "hive_id": h["id"]}, headers=beekeeper)
    assert r.status_code == 201, r.text
    assert Decimal(r.json()["total_value"]) == 180 and r.json()["apiary_id"] == apiary["id"]
    assert client.post("/api/products", json={"product_type": "PROPOLIS", "quantity": 0, "unit": "G"},
                       headers=beekeeper).status_code == 422
    assert len(client.get("/api/products", params={"year": Y}, headers=beekeeper).json()) == 1


# ---------- US2 movement ----------

def test_move_hive(client, beekeeper, apiary, apiary2):
    h = hive(client, beekeeper, apiary["id"], "5")
    r = client.post(f"/api/hives/{h['id']}/move", json={"to_apiary_id": apiary2["id"], "reason": "Кочёвка"},
                    headers=beekeeper)
    assert r.status_code == 200, r.text
    assert r.json()["id"] == h["id"] and r.json()["apiary"]["name"] == "Горная"
    m = client.get(f"/api/hives/{h['id']}/movements", headers=beekeeper).json()
    assert m[0]["from_apiary"] == "Пасека №1" and m[0]["to_apiary"] == "Горная" and m[0]["performed_by"] == "Иван"


def test_move_number_conflict(client, beekeeper, apiary, apiary2):
    h = hive(client, beekeeper, apiary["id"], "5")
    hive(client, beekeeper, apiary2["id"], "5")
    r = client.post(f"/api/hives/{h['id']}/move", json={"to_apiary_id": apiary2["id"]}, headers=beekeeper)
    assert r.status_code == 409 and "новый номер" in r.json()["detail"]
    r = client.post(f"/api/hives/{h['id']}/move", json={"to_apiary_id": apiary2["id"], "new_hive_number": "55"},
                    headers=beekeeper)
    assert r.status_code == 200 and r.json()["hive_number"] == "55"


def test_move_refusals(client, beekeeper, apiary, as_role):
    h = hive(client, beekeeper, apiary["id"], "5")
    r = client.post(f"/api/hives/{h['id']}/move", json={"to_apiary_id": apiary["id"]}, headers=beekeeper)
    assert r.status_code == 422
    assert client.post(f"/api/hives/{h['id']}/move", json={"to_apiary_id": apiary["id"]},
                       headers=as_role("ASSISTANT")).status_code == 403


# ---------- US3 swarm / split / merge ----------

def test_split_without_queen(client, beekeeper, apiary):
    src = hive(client, beekeeper, apiary["id"], "10")
    r = client.post(f"/api/hives/{src['id']}/split", json={"new_hive_number": "35"}, headers=beekeeper)
    assert r.status_code == 201, r.text
    new = r.json()["new_hive"]
    assert new["hive_number"] == "35" and new["status"] == "QUEENLESS"
    assert new["current_family"]["origin"] == "SPLIT"
    assert r.json()["source"]["status"] == "ACTIVE"
    src_events = [i for i in client.get(f"/api/hives/{src['id']}/timeline", headers=beekeeper).json() if i["kind"] == "event"]
    assert any(e["action"] == "split" and e["new_value"]["new_hive_number"] == "35" for e in src_events)
    new_events = client.get(f"/api/hives/{new['id']}/timeline", headers=beekeeper).json()
    assert any(e.get("action") == "split_created" for e in new_events)


def test_split_with_free_queen_into_empty_hive(client, beekeeper, apiary):
    src = hive(client, beekeeper, apiary["id"], "10")
    empty = hive(client, beekeeper, apiary["id"], "11", family=False)
    q = queen(client, beekeeper, "M-300")
    r = client.post(f"/api/hives/{src['id']}/split", json={"target_hive_id": empty["id"], "queen_id": q["id"]},
                    headers=beekeeper)
    assert r.status_code == 201, r.text
    new = r.json()["new_hive"]
    assert new["id"] == empty["id"] and new["current_queen"]["queen_code"] == "M-300" and new["status"] == "ACTIVE"


def test_split_into_populated_hive_refused(client, beekeeper, apiary):
    src = hive(client, beekeeper, apiary["id"], "10")
    busy = hive(client, beekeeper, apiary["id"], "11")
    r = client.post(f"/api/hives/{src['id']}/split", json={"target_hive_id": busy["id"]}, headers=beekeeper)
    assert r.status_code == 409 and "уже живёт семья" in r.json()["detail"]


def test_merge_into_source_keeping_other_queen(client, beekeeper, apiary):
    h15 = hive(client, beekeeper, apiary["id"], "15")
    h18 = hive(client, beekeeper, apiary["id"], "18")
    q15 = queen(client, beekeeper, "Q15", h15["id"])
    q18 = queen(client, beekeeper, "Q18", h18["id"])
    r = client.post("/api/merges", json={"source_hive_ids": [h15["id"], h18["id"]], "target_hive_id": h15["id"],
                                         "keep_queen_id": q18["id"]}, headers=beekeeper)
    assert r.status_code == 201, r.text
    assert r.json()["id"] == h15["id"] and r.json()["current_queen"]["queen_code"] == "Q18"
    assert client.get(f"/api/queens/{q15['id']}", headers=beekeeper).json()["status"] == "REPLACED"
    h18_now = get(client, beekeeper, h18["id"])
    assert h18_now["status"] == "MERGED" and h18_now["is_archived"] and h18_now["current_family"] is None
    fam = client.get(f"/api/hives/{h18['id']}/families", headers=beekeeper).json()
    assert fam[0]["status"] == "MERGED"
    target_events = client.get(f"/api/hives/{h15['id']}/timeline", headers=beekeeper).json()
    merge_ev = next(e for e in target_events if e.get("action") == "merge_target")
    assert merge_ev["new_value"]["source_hive_numbers"] == ["18"]


def test_merge_into_new_hive(client, beekeeper, apiary):
    a = hive(client, beekeeper, apiary["id"], "15", strength="WEAK")
    b = hive(client, beekeeper, apiary["id"], "18", strength="WEAK")
    r = client.post("/api/merges", json={"source_hive_ids": [a["id"], b["id"]], "new_hive_number": "40"},
                    headers=beekeeper)
    assert r.status_code == 201, r.text
    t = r.json()
    assert t["hive_number"] == "40" and t["current_family"]["origin"] == "MERGE"
    assert t["current_family"]["strength"] == "MEDIUM"  # two weak colonies make a medium one
    assert t["status"] == "QUEENLESS"
    assert get(client, beekeeper, a["id"])["status"] == "MERGED" and get(client, beekeeper, b["id"])["status"] == "MERGED"


@pytest.mark.parametrize("bad", ["one", "archived", "foreign_queen"])
def test_merge_refusals(client, beekeeper, apiary, bad):
    a = hive(client, beekeeper, apiary["id"], "1")
    b = hive(client, beekeeper, apiary["id"], "2")
    body = {"source_hive_ids": [a["id"], b["id"]], "target_hive_id": a["id"]}
    if bad == "one":
        body["source_hive_ids"] = [a["id"]]
    elif bad == "archived":
        client.put(f"/api/hives/{b['id']}", json={"status": "SOLD"}, headers=beekeeper)
    else:
        body["keep_queen_id"] = queen(client, beekeeper, "FREE")["id"]
    assert client.post("/api/merges", json=body, headers=beekeeper).status_code in (409, 422)


def test_swarm_captured_into_new_hive(client, beekeeper, apiary):
    src = hive(client, beekeeper, apiary["id"], "7")
    r = client.post(f"/api/hives/{src['id']}/swarms", json={"captured": True, "new_hive_number": "41",
                                                            "actions": "Снят с яблони"}, headers=beekeeper)
    assert r.status_code == 201, r.text
    new = r.json()["new_hive"]
    assert new["hive_number"] == "41" and new["current_family"]["origin"] == "SWARM"
    ev = [e for e in client.get(f"/api/hives/{src['id']}/timeline", headers=beekeeper).json() if e.get("action") == "swarmed"]
    assert ev and ev[0]["new_value"]["new_hive_number"] == "41"


def test_swarm_not_captured(client, beekeeper, apiary):
    src = hive(client, beekeeper, apiary["id"], "7")
    r = client.post(f"/api/hives/{src['id']}/swarms", json={"swarm_count": 2}, headers=beekeeper)
    assert r.status_code == 201 and r.json()["new_hive"] is None
    r = client.post(f"/api/hives/{src['id']}/swarms", json={"captured": False, "new_hive_number": "9"}, headers=beekeeper)
    assert r.status_code == 422 and "пойманный" in r.json()["detail"]


# ---------- US4 wintering ----------

def test_wintering_lifecycle_and_duplicate(client, beekeeper, apiary):
    h = hive(client, beekeeper, apiary["id"], "3")
    season = f"{Y}/{Y + 1}"
    r = client.post(f"/api/hives/{h['id']}/winterings", json={"season": season, "food_kg": 18, "frames_count": 8,
                                                              "pre_winter_strength": "STRONG"}, headers=beekeeper)
    assert r.status_code == 201, r.text
    assert client.post(f"/api/hives/{h['id']}/winterings", json={"season": season}, headers=beekeeper).status_code == 409
    assert client.post(f"/api/hives/{h['id']}/winterings", json={"season": "2026-2027"}, headers=beekeeper).status_code == 422
    r = client.put(f"/api/winterings/{r.json()['id']}/finish", json={"result": "STRONG", "spring_strength": "STRONG"},
                   headers=beekeeper)
    assert r.status_code == 200 and r.json()["hive"]["current_family"]["strength"] == "STRONG"


def test_wintering_died_closes_family(client, beekeeper, apiary):
    h = hive(client, beekeeper, apiary["id"], "3")
    q = queen(client, beekeeper, "Q3", h["id"])
    w = client.post(f"/api/hives/{h['id']}/winterings",
                    json={"season": f"{Y - 1}/{Y}", "start_date": (TODAY - timedelta(days=100)).isoformat()},
                    headers=beekeeper).json()
    r = client.put(f"/api/winterings/{w['id']}/finish", json={"result": "DIED"}, headers=beekeeper)
    assert r.status_code == 200, r.text
    assert r.json()["hive"]["status"] == "EMPTY" and r.json()["hive"]["current_family"] is None
    assert client.get(f"/api/queens/{q['id']}", headers=beekeeper).json()["status"] == "DEAD"
    assert client.get(f"/api/hives/{h['id']}/families", headers=beekeeper).json()[0]["status"] == "DEAD"
    again = client.put(f"/api/winterings/{w['id']}/finish", json={"result": "DIED"}, headers=beekeeper)
    assert again.status_code == 409


def test_wintering_end_before_start(client, beekeeper, apiary):
    h = hive(client, beekeeper, apiary["id"], "3")
    w = client.post(f"/api/hives/{h['id']}/winterings", json={"season": f"{Y}/{Y + 1}"}, headers=beekeeper).json()
    r = client.put(f"/api/winterings/{w['id']}/finish",
                   json={"result": "WEAK", "end_date": (TODAY - timedelta(days=3)).isoformat()}, headers=beekeeper)
    assert r.status_code == 422


def test_timeline_includes_honey(client, beekeeper, apiary):
    h = hive(client, beekeeper, apiary["id"], "1")
    harvest(client, beekeeper, h["id"], weight_kg=8, honey_type="Акация")
    items = client.get(f"/api/hives/{h['id']}/timeline", headers=beekeeper).json()
    honey_item = next(i for i in items if i["kind"] == "honey")
    assert honey_item["title"] == "Откачка мёда №1" and honey_item["details"][0] == "8 кг, Акация"
