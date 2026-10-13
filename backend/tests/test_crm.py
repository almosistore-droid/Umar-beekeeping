"""Stage 7 CRM: customers, expenses, sales and payments, debts, orders, profit; roles; money arithmetic."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

TODAY = datetime.now(timezone.utc).date()
Y = TODAY.year
D = Decimal


@pytest.fixture
def customer(client, beekeeper):
    r = client.post("/api/crm/customers", json={"name": "Фарход", "phone": "+992 90 123-45-67", "city": "Душанбе"},
                    headers=beekeeper)
    assert r.status_code == 201, r.text
    return r.json()


def honey(qty, price, **kw):
    return {"category": "HONEY", "quantity": qty, "unit": "KG", "price_per_unit": price, **kw}


def sale(client, headers, items, **kw):
    r = client.post("/api/crm/sales", json={"items": items, **kw}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ---------- customers ----------

def test_customer_phone_normalised_and_unique(client, beekeeper, customer):
    assert customer["phone"] == "+992901234567" and customer["debt"] == "0.00"
    r = client.post("/api/crm/customers", json={"name": "Другой", "phone": "+992901234567"}, headers=beekeeper)
    assert r.status_code == 409 and "Фарход" in r.json()["detail"]
    r = client.post("/api/crm/customers", json={"name": "Б", "phone": "12"}, headers=beekeeper)
    assert r.status_code == 422
    assert {e["field"] for e in r.json()["errors"]} == {"name", "phone"}


def test_customer_search_and_archive(client, beekeeper, customer):
    client.post("/api/crm/customers", json={"name": "Зарина", "city": "Худжанд"}, headers=beekeeper)
    names = lambda q: [c["name"] for c in client.get("/api/crm/customers", params={"q": q}, headers=beekeeper).json()]
    assert names("фар") == ["Фарход"] and names("1234") == ["Фарход"] and names("худж") == ["Зарина"]
    r = client.put(f"/api/crm/customers/{customer['id']}", json={"is_archived": True}, headers=beekeeper)
    assert r.status_code == 200 and r.json()["is_archived"] is True
    assert names("") == ["Зарина"]
    r = client.post("/api/crm/sales", json={"items": [honey(1, 100)], "customer_id": customer["id"]}, headers=beekeeper)
    assert r.status_code == 409 and "в архиве" in r.json()["detail"]


# ---------- sales & payments ----------

def test_sale_full_payment_totals(client, beekeeper, customer):
    s = sale(client, beekeeper, [honey(12.5, 80), {"category": "WAX", "quantity": 2, "unit": "KG", "price_per_unit": 150}],
             customer_id=customer["id"])
    assert s["total"] == "1300.00" and s["paid"] == "1300.00" and s["debt"] == "0.00" and s["state"] == "paid"
    assert [i["total"] for i in s["items"]] == ["1000.00", "300.00"]
    assert s["payments"][0]["method"] == "CASH" and s["author"]


def test_credit_and_partial_payments_make_debts(client, beekeeper, customer):
    s = sale(client, beekeeper, [honey(10, 100)], customer_id=customer["id"], payment="partial", paid_amount=300,
             method="TRANSFER")
    assert s["state"] == "partial" and s["debt"] == "700.00"
    r = client.post(f"/api/crm/sales/{s['id']}/payments", json={"amount": 800}, headers=beekeeper)
    assert r.status_code == 422 and "больше долга" in r.json()["detail"]
    r = client.post(f"/api/crm/sales/{s['id']}/payments", json={"amount": 200, "method": "CARD"}, headers=beekeeper)
    assert r.status_code == 201 and r.json()["debt"] == "500.00"
    sale(client, beekeeper, [honey(1, 250)], customer_id=customer["id"], payment="credit")
    debts = client.get("/api/crm/debts", headers=beekeeper).json()
    assert len(debts) == 1 and debts[0]["customer"]["name"] == "Фарход" and debts[0]["debt"] == "750.00"
    assert len(debts[0]["sales"]) == 2
    card = client.get(f"/api/crm/customers/{customer['id']}", headers=beekeeper).json()
    assert card["bought"] == "1250.00" and card["paid"] == "500.00" and card["debt"] == "750.00" and card["sales_count"] == 2
    # paying everything clears the debt
    client.post(f"/api/crm/sales/{s['id']}/payments", json={"amount": 500}, headers=beekeeper)
    r = client.post(f"/api/crm/sales/{s['id']}/payments", json={"amount": 1}, headers=beekeeper)
    assert r.status_code == 409 and "полностью оплачена" in r.json()["detail"]


def test_sale_validation(client, beekeeper, customer):
    r = client.post("/api/crm/sales", json={"items": []}, headers=beekeeper)
    assert r.status_code == 422
    r = client.post("/api/crm/sales", json={"items": [honey(0, 100)]}, headers=beekeeper)
    assert r.status_code == 422 and r.json()["errors"][0]["field"].startswith("items")
    r = client.post("/api/crm/sales", json={"items": [honey(1, 100)], "payment": "credit"}, headers=beekeeper)
    assert r.status_code == 422 and "выберите клиента" in r.json()["detail"]
    r = client.post("/api/crm/sales", json={"items": [honey(1, 100)], "customer_id": customer["id"], "payment": "partial"},
                    headers=beekeeper)
    assert r.status_code == 422 and "сколько заплатили" in r.json()["detail"]
    r = client.post("/api/crm/sales", json={"items": [honey(1, 100)], "customer_id": customer["id"],
                                            "payment": "partial", "paid_amount": 101}, headers=beekeeper)
    assert r.status_code == 422 and "больше суммы" in r.json()["detail"]
    future = (TODAY + timedelta(days=5)).isoformat()
    r = client.post("/api/crm/sales", json={"items": [honey(1, 100)], "sale_date": future}, headers=beekeeper)
    assert r.status_code == 422 and "в будущем" in r.json()["detail"]


def test_cancel_sale_rules(client, beekeeper, customer):
    paid = sale(client, beekeeper, [honey(1, 100)])
    r = client.post(f"/api/crm/sales/{paid['id']}/cancel", json={"reason": "Ошибка"}, headers=beekeeper)
    assert r.status_code == 409 and "есть оплата" in r.json()["detail"]
    credit = sale(client, beekeeper, [honey(2, 100)], customer_id=customer["id"], payment="credit")
    r = client.post(f"/api/crm/sales/{credit['id']}/cancel", json={"reason": "Клиент передумал"}, headers=beekeeper)
    assert r.status_code == 200 and r.json()["state"] == "cancelled" and r.json()["debt"] == "0.00"
    assert client.get("/api/crm/debts", headers=beekeeper).json() == []
    assert len(client.get("/api/crm/sales", headers=beekeeper).json()) == 1
    assert len(client.get("/api/crm/sales", params={"include_cancelled": True}, headers=beekeeper).json()) == 2
    r = client.post(f"/api/crm/sales/{credit['id']}/cancel", json={"reason": "Ещё раз"}, headers=beekeeper)
    assert r.status_code == 409


# ---------- expenses ----------

def test_expenses_correct_and_cancel(client, beekeeper):
    r = client.post("/api/crm/expenses", json={"category": "FUEL", "amount": 250, "description": "Бензин на кочёвку"},
                    headers=beekeeper)
    assert r.status_code == 201, r.text
    e = r.json()
    assert e["expense_date"] == TODAY.isoformat() and e["amount"] == "250.00"
    r = client.put(f"/api/crm/expenses/{e['id']}", json={"amount": 300, "comment": "Чек нашёлся"}, headers=beekeeper)
    assert r.json()["amount"] == "300.00"
    for bad in ({"category": "FUEL", "amount": 0}, {"category": "FUEL", "amount": -5}, {"category": "NOPE", "amount": 5}):
        assert client.post("/api/crm/expenses", json=bad, headers=beekeeper).status_code == 422
    r = client.post(f"/api/crm/expenses/{e['id']}/cancel", json={"reason": "Записал дважды"}, headers=beekeeper)
    assert r.status_code == 200 and r.json()["cancel_reason"] == "Записал дважды"
    assert client.put(f"/api/crm/expenses/{e['id']}", json={"amount": 1}, headers=beekeeper).status_code == 409
    assert client.get("/api/crm/expenses", headers=beekeeper).json() == []
    r = client.post(f"/api/crm/expenses/{e['id']}/cancel", json={"reason": "a"}, headers=beekeeper)
    assert r.status_code == 422


# ---------- orders ----------

def test_order_flow_deliver_creates_sale(client, beekeeper, customer):
    due = (TODAY + timedelta(days=3)).isoformat()
    r = client.post("/api/crm/orders", json={"customer_id": customer["id"], "due_date": due, "items": [honey(10, 90)],
                                             "notes": "3 банки по 3 л"}, headers=beekeeper)
    assert r.status_code == 201, r.text
    o = r.json()
    assert o["status"] == "NEW" and o["total"] == "900.00" and o["overdue"] is False and o["sale_id"] is None
    r = client.put(f"/api/crm/orders/{o['id']}", json={"items": [honey(12, 90)], "status": "READY"}, headers=beekeeper)
    assert r.json()["status"] == "READY" and r.json()["total"] == "1080.00"
    r = client.post(f"/api/crm/orders/{o['id']}/deliver", json={"payment": "partial", "paid_amount": 500}, headers=beekeeper)
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["order_id"] == o["id"] and s["total"] == "1080.00" and s["debt"] == "580.00"
    o = client.get(f"/api/crm/orders/{o['id']}", headers=beekeeper).json()
    assert o["status"] == "DELIVERED" and o["sale_state"] == "partial" and o["sale_debt"] == "580.00"
    assert client.post(f"/api/crm/orders/{o['id']}/deliver", json={}, headers=beekeeper).status_code == 409
    assert client.put(f"/api/crm/orders/{o['id']}", json={"notes": "x"}, headers=beekeeper).status_code == 409
    # sale of an order is cancelled through the order; with a payment neither can be cancelled
    r = client.post(f"/api/crm/sales/{s['id']}/cancel", json={"reason": "Ошибка"}, headers=beekeeper)
    assert r.status_code == 409
    r = client.post(f"/api/crm/orders/{o['id']}/cancel", json={"reason": "Ошибка"}, headers=beekeeper)
    assert r.status_code == 409 and "есть оплата" in r.json()["detail"]


def test_order_cancel_and_status_rules(client, beekeeper, customer):
    o = client.post("/api/crm/orders", json={"customer_id": customer["id"], "items": [honey(1, 100)]}, headers=beekeeper).json()
    r = client.post(f"/api/crm/orders/{o['id']}/deliver", json={"payment": "credit"}, headers=beekeeper)
    assert r.status_code == 200
    r = client.post(f"/api/crm/orders/{o['id']}/cancel", json={"reason": "Вернул банку"}, headers=beekeeper)
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED" and r.json()["sale_state"] == "cancelled"
    assert client.get("/api/crm/debts", headers=beekeeper).json() == []
    past = (TODAY - timedelta(days=10)).isoformat()
    r = client.post("/api/crm/orders", json={"customer_id": customer["id"], "items": [honey(1, 1)], "order_date": past,
                                             "due_date": (TODAY - timedelta(days=11)).isoformat()}, headers=beekeeper)
    assert r.status_code == 422 and "Срок выдачи раньше" in r.json()["detail"]
    late = client.post("/api/crm/orders", json={"customer_id": customer["id"], "items": [honey(1, 1)], "order_date": past,
                                                "due_date": (TODAY - timedelta(days=1)).isoformat()}, headers=beekeeper).json()
    assert late["overdue"] is True
    open_ids = [x["id"] for x in client.get("/api/crm/orders", params={"open_only": True}, headers=beekeeper).json()]
    assert open_ids == [late["id"]]


# ---------- summary & profit ----------

def test_summary_profit_and_stock(client, beekeeper, customer):
    ap = client.post("/api/apiaries", json={"name": "П"}, headers=beekeeper).json()
    h = client.post("/api/hives", json={"apiary_id": ap["id"], "hive_number": "1", "family": {}}, headers=beekeeper).json()
    client.post(f"/api/hives/{h['id']}/honey", json={"weight_kg": 40}, headers=beekeeper)
    sale(client, beekeeper, [honey(10, 100)])  # 1000 paid
    sale(client, beekeeper, [honey(5, 100), {"category": "PROPOLIS", "quantity": 100, "unit": "G", "price_per_unit": 2}],
         customer_id=customer["id"], payment="partial", paid_amount=200)  # 700, paid 200
    client.post("/api/crm/expenses", json={"category": "FEED", "amount": 300}, headers=beekeeper)
    client.post("/api/crm/expenses", json={"category": "MEDICINE", "amount": 150}, headers=beekeeper)
    cancelled = client.post("/api/crm/expenses", json={"category": "FUEL", "amount": 999}, headers=beekeeper).json()
    client.post(f"/api/crm/expenses/{cancelled['id']}/cancel", json={"reason": "Ошибка"}, headers=beekeeper)
    client.post("/api/crm/orders", json={"customer_id": customer["id"], "items": [honey(3, 100)]}, headers=beekeeper)

    s = client.get("/api/crm/summary", params={"year": Y, "month": TODAY.month}, headers=beekeeper).json()
    assert (D(s["income"]), D(s["expenses"]), D(s["profit"])) == (1700, 450, 1250)
    assert D(s["received"]) == 1200 and D(s["debts_total"]) == 500 and s["debtors"] == 1 and s["open_orders"] == 1
    assert D(s["honey_stock_kg"]) == 25 and s["currency"] == "смн"
    assert D(s["income_by_month"][TODAY.month - 1]) == 1700 and D(s["expenses_by_month"][TODAY.month - 1]) == 450
    assert [(x["label"], D(x["amount"])) for x in s["income_by_category"]] == [("Мёд", 1500), ("Прополис", 200)]
    assert [x["label"] for x in s["expenses_by_category"]] == ["Корм", "Лекарства"]

    d = client.get("/api/dashboard", headers=beekeeper).json()["finance"]
    assert (D(d["income"]), D(d["expenses"]), D(d["profit"]), D(d["debts_total"])) == (1700, 450, 1250, 500)
    f = client.get(f"/api/reports/yearly/{Y}", headers=beekeeper).json()["finance"]
    assert f["visible"] and (D(f["income"]), D(f["profit"])) == (1700, 1250)
    assert f["expenses_by_category"][0]["label"] == "Корм"


# ---------- roles & audit ----------

@pytest.mark.parametrize("role", ["ASSISTANT", "VIEWER"])
def test_crm_closed_to_assistants_and_viewers(client, as_role, role):
    headers = as_role(role)
    for path in ("/api/crm/summary", "/api/crm/customers", "/api/crm/sales", "/api/crm/expenses", "/api/crm/orders",
                 "/api/crm/debts"):
        assert client.get(path, headers=headers).status_code == 403, path
    assert client.post("/api/crm/expenses", json={"category": "FEED", "amount": 1}, headers=headers).status_code == 403
    assert client.get("/api/dashboard", headers=headers).json()["finance"] is None
    f = client.get(f"/api/reports/yearly/{Y}", headers=headers).json()["finance"]
    assert f["visible"] is False and f["income"] is None


def test_admin_has_crm(client, as_role):
    assert client.get("/api/crm/summary", headers=as_role("ADMIN")).status_code == 200


def test_writes_are_audited(client, beekeeper, customer, db):
    from sqlalchemy import select
    from app.models.audit import AuditLog
    s = sale(client, beekeeper, [honey(1, 100)], customer_id=customer["id"], payment="credit")
    client.post(f"/api/crm/sales/{s['id']}/payments", json={"amount": 40}, headers=beekeeper)
    actions = [a for a, in db.execute(select(AuditLog.action).where(AuditLog.entity_id == s["id"])
                                      .order_by(AuditLog.created_at)).all()]
    assert actions == ["created", "payment"]
    assert db.scalar(select(AuditLog.action).where(AuditLog.entity_type == "customer")) == "created"
