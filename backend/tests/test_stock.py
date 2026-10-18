"""Warehouse: items, receipts / use / inventory, frame preparation by the norms, feedings and treatments
writing off automatically, honey stock, low-stock warnings, roles."""
from datetime import timedelta
from decimal import Decimal

import pytest

from app.config import get_settings
from app.models import StockMovement
from app.schemas.common import today as app_today
from app.services import notification_service as ns

TODAY = app_today()


@pytest.fixture
def people(as_role):
    return {"admin": as_role("ADMIN", 1000), "keeper": as_role("BEEKEEPER", 3000),
            "assistant": as_role("ASSISTANT", 4001), "viewer": as_role("VIEWER", 4002)}


@pytest.fixture
def keeper(people):
    return people["keeper"]


@pytest.fixture
def hive(client, keeper):
    ap = client.post("/api/apiaries", json={"name": "Горная"}, headers=keeper).json()
    return client.post("/api/hives", json={"apiary_id": ap["id"], "hive_number": "7", "family": {"strength": "MEDIUM"}},
                       headers=keeper).json()


def stock(client, headers):
    r = client.get("/api/stock", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def by_code(client, headers, code):
    return next(i for i in stock(client, headers)["items"] if i["code"] == code)


def receive(client, headers, item_id, qty):
    r = client.post(f"/api/stock/items/{item_id}/movements", json={"kind": "RECEIPT", "quantity": str(qty)},
                    headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_system_items_and_norms_are_there(client, keeper):
    data = stock(client, keeper)
    codes = [i["code"] for i in data["items"]]
    assert codes[:4] == ["frames_empty", "frames_ready", "foundation", "wire"]
    assert {"sugar", "candy", "protein"} <= set(codes)
    assert Decimal(data["norms"]["wire_m_per_frame"]) == 3
    assert Decimal(data["norms"]["foundation_g_per_frame"]) == 110
    assert Decimal(data["honey_kg"]) == 0


def test_frame_preparation_writes_off_by_the_norms(client, keeper):
    client.put("/api/stock/norms", json={"wire_m_per_frame": "2.5", "foundation_g_per_frame": "120",
                                         "sugar_kg_per_l_syrup": "0.63", "sugar_kg_per_kg_syrup": "0.5"}, headers=keeper)
    wire, foundation = by_code(client, keeper, "wire"), by_code(client, keeper, "foundation")
    empty = by_code(client, keeper, "frames_empty")
    receive(client, keeper, wire["id"], 100)
    receive(client, keeper, foundation["id"], "5")
    receive(client, keeper, empty["id"], 30)

    r = client.post("/api/stock/frame-preps", json={"frames": 20}, headers=keeper)
    assert r.status_code == 201, r.text
    lines = {line["name"]: line for line in r.json()["lines"]}
    assert Decimal(lines["Проволока"]["quantity"]) == Decimal("-50")          # 20 × 2.5 m
    assert Decimal(lines["Проволока"]["balance_after"]) == Decimal("50")
    assert Decimal(lines["Вощина"]["quantity"]) == Decimal("-2.4")            # 20 × 120 g
    assert Decimal(lines["Рамки пустые"]["balance_after"]) == 10
    assert Decimal(lines["Рамки с вощиной"]["quantity"]) == 20

    # later norm changes do not rewrite the batch; cancelling the batch returns everything
    prep = r.json()["prep"]
    assert Decimal(prep["wire_m_per_frame"]) == Decimal("2.5")
    r = client.post(f"/api/stock/frame-preps/{prep['id']}/cancel", json={"reason": "ошибка"}, headers=keeper)
    assert r.status_code == 200
    assert Decimal(by_code(client, keeper, "wire")["quantity"]) == 100
    assert Decimal(by_code(client, keeper, "frames_ready")["quantity"]) == 0


def test_frame_preparation_may_go_below_zero_and_marks_low(client, keeper):
    r = client.post("/api/stock/frame-preps", json={"frames": 10}, headers=keeper)
    assert r.status_code == 201
    wire = by_code(client, keeper, "wire")
    assert Decimal(wire["quantity"]) == -30 and wire["low"] is True


def test_syrup_feeding_writes_off_sugar_and_correction_rewrites_it(client, keeper, hive, db):
    sugar = by_code(client, keeper, "sugar")
    receive(client, keeper, sugar["id"], 50)
    r = client.post(f"/api/hives/{hive['id']}/feedings",
                    json={"feed_type": "SUGAR_SYRUP", "quantity": "2", "unit": "L"}, headers=keeper)
    assert r.status_code == 201, r.text
    feeding = r.json()["feeding"]
    assert Decimal(by_code(client, keeper, "sugar")["quantity"]) == Decimal("48.74")  # 2 l × 0.63

    r = client.put(f"/api/feedings/{feeding['id']}", json={"feed_type": "SUGAR_SYRUP", "quantity": "3000", "unit": "ML",
                                                           "comment": "было 3 л"}, headers=keeper)
    assert r.status_code == 200, r.text
    assert Decimal(by_code(client, keeper, "sugar")["quantity"]) == Decimal("48.11")
    moves = db.query(StockMovement).filter(StockMovement.feeding_id == feeding["id"]).all()
    assert len(moves) == 2 and sum(1 for m in moves if m.cancelled_at is None) == 1

    # changed to a feed that is not tracked → the write-off is cancelled
    client.put(f"/api/feedings/{feeding['id']}", json={"feed_type": "MEDICATED", "quantity": "1", "unit": "L"},
               headers=keeper)
    assert Decimal(by_code(client, keeper, "sugar")["quantity"]) == 50

    details = client.get(f"/api/stock/items/{sugar['id']}", headers=keeper).json()
    feeding_moves = [m for m in details["movements"] if m["kind"] == "FEEDING"]
    assert feeding_moves[0]["hive_number"] == "7"


def test_candy_protein_and_honey_feedings(client, keeper, hive):
    client.post(f"/api/hives/{hive['id']}/feedings", json={"feed_type": "CANDY", "quantity": "500", "unit": "G"},
                headers=keeper)
    client.post(f"/api/hives/{hive['id']}/feedings", json={"feed_type": "POLLEN_SUBSTITUTE", "quantity": "1",
                                                          "unit": "KG"}, headers=keeper)
    assert Decimal(by_code(client, keeper, "candy")["quantity"]) == Decimal("-0.5")
    assert Decimal(by_code(client, keeper, "protein")["quantity"]) == -1

    client.post(f"/api/hives/{hive['id']}/honey", json={"weight_kg": "20"}, headers=keeper)
    client.post(f"/api/hives/{hive['id']}/feedings", json={"feed_type": "HONEY", "quantity": "1500", "unit": "G"},
                headers=keeper)
    assert Decimal(stock(client, keeper)["honey_kg"]) == Decimal("18.5")


def test_treatment_takes_the_chosen_medicine(client, keeper, hive):
    r = client.post("/api/stock/items", json={"name": "Бипин", "category": "MEDICINE", "unit": "ML",
                                              "min_quantity": "5", "initial_quantity": "10"}, headers=keeper)
    assert r.status_code == 201, r.text
    med = r.json()
    assert Decimal(med["quantity"]) == 10 and med["low"] is False

    body = {"medication": "Бипин", "stock_item_id": med["id"], "stock_quantity": "6"}
    r = client.post(f"/api/hives/{hive['id']}/treatments", json=body, headers=keeper)
    assert r.status_code == 201, r.text
    t = r.json()["treatment"]
    assert t["stock_item_id"] == med["id"] and Decimal(t["stock_quantity"]) == 6
    item = client.get(f"/api/stock/items/{med['id']}", headers=keeper).json()["item"]
    assert Decimal(item["quantity"]) == 4 and item["low"] is True

    # removing the medicine from the record returns it
    r = client.put(f"/api/treatments/{t['id']}", json={"medication": "Бипин"}, headers=keeper)
    assert r.status_code == 200 and r.json()["treatment"]["stock_item_id"] is None
    assert Decimal(client.get(f"/api/stock/items/{med['id']}", headers=keeper).json()["item"]["quantity"]) == 10

    r = client.post(f"/api/hives/{hive['id']}/treatments", json={"medication": "Бипин", "stock_item_id": med["id"]},
                    headers=keeper)
    assert r.status_code == 422


def test_consumption_inventory_and_cancel(client, keeper):
    sugar = by_code(client, keeper, "sugar")
    receive(client, keeper, sugar["id"], 10)
    url = f"/api/stock/items/{sugar['id']}/movements"
    r = client.post(url, json={"kind": "CONSUMPTION", "quantity": "12"}, headers=keeper)
    assert r.status_code == 409 and "только 10" in r.json()["detail"]
    r = client.post(url, json={"kind": "CONSUMPTION", "quantity": "4"}, headers=keeper)
    assert Decimal(r.json()["quantity"]) == 6
    r = client.post(url, json={"kind": "INVENTORY", "quantity": "5.5"}, headers=keeper)
    assert Decimal(r.json()["quantity"]) == Decimal("5.5")
    assert client.post(url, json={"kind": "INVENTORY", "quantity": "5.5"}, headers=keeper).status_code == 422

    moves = client.get(f"/api/stock/items/{sugar['id']}", headers=keeper).json()["movements"]
    inventory = moves[0]
    assert inventory["kind"] == "INVENTORY" and Decimal(inventory["quantity"]) == Decimal("-0.5")
    r = client.post(f"/api/stock/movements/{inventory['id']}/cancel", json={"reason": "пересчитали"}, headers=keeper)
    assert Decimal(r.json()["quantity"]) == 6
    again = client.post(f"/api/stock/movements/{inventory['id']}/cancel", json={"reason": "x"}, headers=keeper)
    assert again.status_code == 409


def test_items_names_archive_and_system_rules(client, keeper):
    r = client.post("/api/stock/items", json={"name": "Сетка", "unit": "PCS"}, headers=keeper)
    item = r.json()
    assert client.post("/api/stock/items", json={"name": "сетка"}, headers=keeper).status_code == 409
    assert client.post(f"/api/stock/items/{item['id']}/archive", headers=keeper).json()["is_archived"] is True
    assert all(i["id"] != item["id"] for i in stock(client, keeper)["items"])
    assert client.post("/api/stock/items", json={"name": "Сетка"}, headers=keeper).status_code == 201
    assert client.post(f"/api/stock/items/{item['id']}/restore", headers=keeper).status_code == 409

    wire = by_code(client, keeper, "wire")
    assert client.post(f"/api/stock/items/{wire['id']}/archive", headers=keeper).status_code == 409
    r = client.put(f"/api/stock/items/{wire['id']}", json={"name": "Проволока", "category": "FRAMES", "unit": "KG"},
                   headers=keeper)
    assert r.status_code == 409
    r = client.put(f"/api/stock/items/{wire['id']}", json={"name": "Проволока нерж.", "category": "FRAMES", "unit": "M",
                                                         "min_quantity": "50"}, headers=keeper)
    assert r.status_code == 200 and r.json()["low"] is True


def test_roles(client, people):
    a, v = people["assistant"], people["viewer"]
    sugar = by_code(client, v, "sugar")  # everyone can look
    assert client.post("/api/stock/items", json={"name": "Банки"}, headers=a).status_code == 403
    assert client.post(f"/api/stock/items/{sugar['id']}/movements", json={"kind": "RECEIPT", "quantity": "5"},
                       headers=v).status_code == 403
    receive(client, a, sugar["id"], 5)
    assert client.post("/api/stock/frame-preps", json={"frames": 2}, headers=a).status_code == 201
    r = client.post(f"/api/stock/items/{sugar['id']}/movements", json={"kind": "INVENTORY", "quantity": "3"}, headers=a)
    assert r.status_code == 403
    assert client.put("/api/stock/norms", json={"wire_m_per_frame": "1", "foundation_g_per_frame": "1",
                                                "sugar_kg_per_l_syrup": "1", "sugar_kg_per_kg_syrup": "1"},
                      headers=a).status_code == 403


def test_low_stock_on_dashboard_and_in_reminders(client, people, db, monkeypatch):
    keeper = people["keeper"]
    sugar = by_code(client, keeper, "sugar")
    client.put(f"/api/stock/items/{sugar['id']}", json={"name": "Сахар", "category": "FEED", "unit": "KG",
                                                       "min_quantity": "20"}, headers=keeper)
    receive(client, keeper, sugar["id"], 8)
    dash = client.get(f"/api/dashboard?year={TODAY.year}", headers=keeper).json()
    assert [i["name"] for i in dash["stock_low"]] == ["Сахар"]

    monkeypatch.setattr(ns, "_wintering", lambda hives, today: [])
    notes = [n for n in ns.collect(db, get_settings(), TODAY) if n.category == ns.STOCK]
    assert notes and notes[0].lines == ("📦 На складе заканчивается: Сахар — осталось 8 кг",)
    assert notes[0].start == "go_stock"
    from app.models import User
    roles = {u.role.value: ns.wants(u, notes[0]) for u in db.query(User).all()}
    assert roles == {"ADMIN": True, "BEEKEEPER": True, "ASSISTANT": False, "VIEWER": False}
    from app.i18n import translate
    assert translate(notes[0].lines[0], "tg") == "📦 Дар анбор тамом шуда истодааст: Шакар — 8 кг монд"


def test_tajik_names_of_system_items(client, keeper):
    headers = {**keeper, "X-Lang": "tg"}
    names = [i["name"] for i in stock(client, headers)["items"] if i["code"]]
    assert "Сахар" not in names and "Вощина" not in names


def test_future_dates_refused(client, keeper):
    r = client.post("/api/stock/frame-preps", json={"frames": 1, "prepared_at": str(TODAY + timedelta(days=2))},
                    headers=keeper)
    assert r.status_code == 422


def test_receipt_with_price_becomes_a_crm_expense(client, people):
    keeper = people["keeper"]
    sugar = by_code(client, keeper, "sugar")
    r = client.post(f"/api/stock/items/{sugar['id']}/movements",
                    json={"kind": "RECEIPT", "quantity": "50", "amount": "650"}, headers=keeper)
    assert r.status_code == 201, r.text
    expenses = client.get("/api/crm/expenses", headers=keeper).json()
    assert len(expenses) == 1
    e = expenses[0]
    assert e["category"] == "FEED" and float(e["amount"]) == 650
    assert e["description"] == "Склад: Сахар 50 кг" and e["stock_item_id"] == sugar["id"]

    # the expense cannot be cancelled / re-priced in CRM: it follows the warehouse receipt
    assert client.post(f"/api/crm/expenses/{e['id']}/cancel", json={"reason": "ошибка"}, headers=keeper).status_code == 409
    assert client.put(f"/api/crm/expenses/{e['id']}", json={"amount": "700"}, headers=keeper).status_code == 409
    assert client.put(f"/api/crm/expenses/{e['id']}", json={"description": "Сахар 50 кг, базар"},
                      headers=keeper).status_code == 200

    move = client.get(f"/api/stock/items/{sugar['id']}", headers=keeper).json()["movements"][0]
    assert float(move["amount"]) == 650 and move["expense_id"] == e["id"]
    client.post(f"/api/stock/movements/{move['id']}/cancel", json={"reason": "ошибка"}, headers=keeper)
    e = client.get("/api/crm/expenses?include_cancelled=true", headers=keeper).json()[0]
    assert e["cancelled_at"] is not None and "Отменён приход на склад" in e["cancel_reason"]


def test_foundation_and_medicine_categories_and_initial_price(client, keeper):
    foundation = by_code(client, keeper, "foundation")
    client.post(f"/api/stock/items/{foundation['id']}/movements",
                json={"kind": "RECEIPT", "quantity": "3", "amount": "540"}, headers=keeper)
    client.post("/api/stock/items", json={"name": "Бипин", "category": "MEDICINE", "unit": "ML",
                                          "initial_quantity": "20", "initial_amount": "45"}, headers=keeper)
    cats = sorted(e["category"] for e in client.get("/api/crm/expenses", headers=keeper).json())
    assert cats == ["FOUNDATION", "MEDICINE"]


def test_price_is_for_managers_only(client, people):
    a, keeper = people["assistant"], people["keeper"]
    sugar = by_code(client, a, "sugar")
    r = client.post(f"/api/stock/items/{sugar['id']}/movements",
                    json={"kind": "RECEIPT", "quantity": "5", "amount": "60"}, headers=a)
    assert r.status_code == 403
    client.post(f"/api/stock/items/{sugar['id']}/movements",
                json={"kind": "RECEIPT", "quantity": "5", "amount": "60"}, headers=keeper)
    moves = client.get(f"/api/stock/items/{sugar['id']}", headers=a).json()["movements"]
    assert moves[0]["amount"] is None
    r = client.post(f"/api/stock/items/{sugar['id']}/movements",
                    json={"kind": "CONSUMPTION", "quantity": "1", "amount": "5"}, headers=keeper)
    assert r.status_code == 403
