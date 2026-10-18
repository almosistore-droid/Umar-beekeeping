"""Stage 10 (optimisation): screens must not run one more SQL query per hive (no N+1).

The same screens are opened with 3 and with 15 hives; the number of queries may not grow with the hives.
"""
from contextlib import contextmanager

import pytest
from sqlalchemy import event

from app.database import engine
from app.schemas.common import today as app_today

TODAY = app_today()


@contextmanager
def count_queries():
    n = {"q": 0}

    def before(*_args, **_kw):
        n["q"] += 1
    event.listen(engine, "before_cursor_execute", before)
    try:
        yield n
    finally:
        event.remove(engine, "before_cursor_execute", before)


def fill(client, headers, apiary, start, count):
    for i in range(start, start + count):
        h = client.post("/api/hives", json={"apiary_id": apiary["id"], "hive_number": str(i),
                                            "family": {"strength": "STRONG"}}, headers=headers).json()
        client.post("/api/queens", json={"queen_code": f"M-{i}", "hive_id": h["id"], "birth_year": TODAY.year}, headers=headers)
        client.post(f"/api/hives/{h['id']}/inspections", json={"strength": "MEDIUM", "frames_total": 8}, headers=headers)
        client.post(f"/api/hives/{h['id']}/honey", json={"weight_kg": "10", "price_per_kg": "80"}, headers=headers)
        client.post(f"/api/hives/{h['id']}/feedings", json={"feed_type": "SUGAR_SYRUP", "quantity": "1", "unit": "L"},
                    headers=headers)


SCREENS = [
    "/api/hives",
    f"/api/dashboard?year={TODAY.year}",
    f"/api/reports/yearly/{TODAY.year}",
    "/api/queens",
    "/api/tasks",
    "/api/stock",
    "/api/rearing",
    f"/api/honey/stats?year={TODAY.year}",
]


def measure(client, headers):
    out = {}
    for url in SCREENS:
        with count_queries() as n:
            r = client.get(url, headers=headers)
        assert r.status_code == 200, (url, r.text)
        out[url] = n["q"]
    return out


def test_screens_do_not_grow_with_the_number_of_hives(client, as_role):
    admin = as_role("ADMIN", 1000)
    apiary = client.post("/api/apiaries", json={"name": "Горная"}, headers=admin).json()
    fill(client, admin, apiary, 1, 3)
    small = measure(client, admin)
    fill(client, admin, apiary, 4, 12)
    big = measure(client, admin)
    grown = {url: (small[url], big[url]) for url in SCREENS if big[url] > small[url] + 2}
    assert not grown, f"queries grow with hives (3 hives → 15 hives): {grown}"


@pytest.mark.parametrize("path", ["", "/timeline", "/check", "/inspections"])
def test_hive_screens_are_bounded(client, as_role, path):
    admin = as_role("ADMIN", 1000)
    apiary = client.post("/api/apiaries", json={"name": "Горная"}, headers=admin).json()
    fill(client, admin, apiary, 1, 1)
    hive = client.get("/api/hives", headers=admin).json()["items"][0]
    for _ in range(10):
        client.post(f"/api/hives/{hive['id']}/inspections", json={"strength": "STRONG", "frames_total": 9}, headers=admin)
    with count_queries() as n:
        assert client.get(f"/api/hives/{hive['id']}{path}", headers=admin).status_code == 200
    assert n["q"] <= 15, f"/api/hives/<id>{path}: {n['q']} queries"
