"""Stage 8: Telegram reminders — what is due, who gets it, sent once, quiet hours, languages, settings."""
from datetime import date, datetime, timedelta, timezone

import pytest

from app.auth.bot_signature import bot_signature
from app.config import get_settings
from app.models import NotificationLog, User, UserRole
from app.schemas.common import app_zone
from app.schemas.common import today as app_today
from app.services import notification_service as ns
from app.services import telegram_bot

TODAY = app_today()
BOT = {"X-Bot-Auth": bot_signature("7000000000:TEST-token-for-unit-tests")}


@pytest.fixture(autouse=True)
def bot_username(monkeypatch):
    monkeypatch.setattr(get_settings(), "telegram_bot_username", "fayzi_bee_bot")


_wintering = ns._wintering


@pytest.fixture(autouse=True)
def no_season(monkeypatch):
    """Seasonal wintering reminders would appear in every test in autumn/spring: tested separately."""
    monkeypatch.setattr(ns, "_wintering", lambda hives, today: [])


@pytest.fixture
def outbox(monkeypatch):
    sent = []
    monkeypatch.setattr(telegram_bot, "send_message", lambda chat, text, button=None: sent.append((chat, text, button)))
    return sent


@pytest.fixture
def people(as_role, db):
    """Telegram IDs: 1000 admin (ADMIN_TELEGRAM_IDS), 3000 beekeeper, 4001 assistant, 4002 viewer."""
    heads = {"admin": as_role("ADMIN", 1000), "keeper": as_role("BEEKEEPER", 3000),
             "assistant": as_role("ASSISTANT", 4001), "viewer": as_role("VIEWER", 4002)}
    return heads


@pytest.fixture
def hive(client, people):
    ap = client.post("/api/apiaries", json={"name": "Горная"}, headers=people["keeper"]).json()
    return client.post("/api/hives", json={"apiary_id": ap["id"], "hive_number": "27", "family": {"strength": "WEAK"}},
                       headers=people["keeper"]).json()


def noon(d: date = TODAY) -> datetime:
    return datetime(d.year, d.month, d.day, 12, tzinfo=app_zone())


def run(db, when=None):
    sent = []
    result = ns.dispatch(db, get_settings(), now=when or noon(), send=lambda c, t, b: sent.append((c, t, b)))
    return result, sent


def chats(sent):
    return sorted(c for c, _, _ in sent)


def test_treatment_due_today_goes_to_field_roles_once(client, db, people, hive):
    client.post(f"/api/hives/{hive['id']}/treatments", json={"medication": "Бипин", "next_treatment_date": TODAY.isoformat()},
                headers=people["assistant"])
    result, sent = run(db)
    assert result["status"] == "ok" and result["sent"] == 3
    assert chats(sent) == [1000, 3000, 4001]  # admin, beekeeper, assistant; never the viewer
    text, button = sent[0][1], sent[0][2]
    assert text.startswith("💊 Сегодня: Повторная обработка: Бипин") and "Улей №27 · Горная" in text
    assert button == ("Открыть улей", f"https://t.me/fayzi_bee_bot?startapp=hive_{hive['id']}")
    assert run(db)[1] == []  # sent once
    assert db.query(NotificationLog).count() == 3


def test_overdue_task_reminded_again_after_three_days(client, db, people, hive):
    due = TODAY - timedelta(days=4)
    client.post(f"/api/hives/{hive['id']}/feedings", json={"feed_type": "SUGAR_SYRUP", "quantity": 2, "unit": "L",
                "fed_at": (due - timedelta(days=7)).isoformat(), "next_feeding_date": due.isoformat()},
                headers=people["keeper"])
    _, sent = run(db)
    texts = {t.split("\n")[0] for c, t, _ in sent if c == 3000}
    assert any(t.startswith("⏰ Просрочено:") for t in texts) and any(t.startswith("⏰ Всё ещё не сделано:") for t in texts)
    assert f"Срок был {due.strftime('%d.%m.%Y')}" in sent[0][1]


def test_inspection_reminder_matches_the_spec(client, db, people, hive):
    last = TODAY - timedelta(days=11)  # next inspection was due 4 days ago
    r = client.post(f"/api/hives/{hive['id']}/inspections",
                    json={"strength": "MEDIUM", "inspected_at": datetime(last.year, last.month, last.day, 12,
                                                                         tzinfo=timezone.utc).isoformat()},
                    headers=people["keeper"])
    assert r.status_code == 201, r.text
    _, sent = run(db)
    mine = [t for c, t, _ in sent if c == 3000]
    assert f"🔍 Напоминание\nУлей №27 давно не осматривался.\nПоследний осмотр: {last.strftime('%d.%m.%Y')}" in mine
    assert any(t.startswith("🔍 Улей №27 всё ещё ждёт осмотра.") for t in mine)  # 3+ days overdue: once more
    # a new inspection moves the next date: nothing more about the old one
    client.post(f"/api/hives/{hive['id']}/inspections", json={"strength": "MEDIUM"}, headers=people["keeper"])
    assert [t for c, t, _ in run(db)[1] if "осмотр" in t.lower()] == []


def test_old_queen_and_queenless(client, db, people, hive):
    client.post("/api/queens", json={"queen_code": "M-7", "hive_id": hive["id"],
                                     "birth_date": (TODAY - timedelta(days=800)).isoformat()}, headers=people["keeper"])
    ap = hive["apiary"]["id"]
    client.post("/api/hives", json={"apiary_id": ap, "hive_number": "6", "status": "QUEENLESS", "family": {}},
                headers=people["keeper"])
    _, sent = run(db)
    mine = [t for c, t, _ in sent if c == 4001]
    assert any(t.startswith("👑 Матке M-7 в улье №27 уже 2 года") and t.endswith("Пора планировать замену.") for t in mine)
    assert any(t.startswith("⚠️ Улей №6 без матки.") for t in mine)
    assert run(db)[1] == []  # once (queenless again next week)


def test_wintering_prep_in_autumn_once_a_year(client, db, people, hive, monkeypatch):
    monkeypatch.setattr(ns, "_wintering", _wintering)
    autumn = date(TODAY.year, 9, 20)
    _, sent = run(db, noon(autumn))
    mine = [t for c, t, _ in sent if c == 3000 and t.startswith("❄️")]
    assert mine == ["❄️ Пора готовить пасеку к зимовке: семей 1, слабых 1.\n"
                    "Проверьте запас корма и утепление, слабые семьи объедините."]
    assert [t for c, t, _ in run(db, noon(autumn + timedelta(days=10)))[1] if t.startswith("❄️")] == []
    spring = date(TODAY.year + 1, 3, 25)
    assert any(t.startswith("🌱 Весенняя ревизия") for _, t, _ in run(db, noon(spring))[1])


def test_crm_only_for_admin_and_beekeeper(client, db, people):
    c = client.post("/api/crm/customers", json={"name": "Фарход", "phone": "+992901234567"}, headers=people["keeper"]).json()
    client.post("/api/crm/sales", json={"customer_id": c["id"], "payment": "credit",
                                        "items": [{"category": "HONEY", "quantity": 10, "unit": "KG", "price_per_unit": 150}]},
                headers=people["keeper"])
    client.post("/api/crm/orders", json={"customer_id": c["id"], "due_date": TODAY.isoformat(),
                                         "items": [{"category": "HONEY", "quantity": 3, "unit": "KG", "price_per_unit": 100}]},
                headers=people["keeper"])
    _, sent = run(db)
    assert chats(sent) == [1000, 1000, 3000, 3000]
    texts = {t for c, t, _ in sent if c == 3000}
    assert "💰 Долг клиента Фарход: 1 500 смн\nТелефон: +992901234567" in texts
    assert "📦 Заказ на сегодня: Фарход — 300 смн (не собран)" in texts
    assert all(b[1].endswith(("startapp=go_debts", "startapp=go_orders")) for _, _, b in sent)


def test_turning_off_and_blocked_people(client, db, people, hive, monkeypatch):
    client.put("/api/notifications/settings", json={"field": False}, headers=people["keeper"])
    client.post(f"/api/hives/{hive['id']}/treatments", json={"medication": "Бипин", "next_treatment_date": TODAY.isoformat()},
                headers=people["keeper"])

    def send(chat, text, button):
        if chat == 4001:
            raise telegram_bot.TelegramBlocked("blocked")
        if chat == 1000:
            raise telegram_bot.TelegramUnavailable("timeout")
    result = ns.dispatch(db, get_settings(), now=noon(), send=send)
    assert result == {"status": "ok", "sent": 0, "failed": 2, "left": 0}
    rows = {r.user_id: r.status for r in db.query(NotificationLog)}
    assistant = db.query(User).filter_by(telegram_id=4001).one()
    assert rows == {assistant.id: "FAILED"}  # blocked: not retried; the admin's timeout is retried next run
    _, sent = run(db)
    assert chats(sent) == [1000]


def test_quiet_hours(client, db, people, hive):
    client.post(f"/api/hives/{hive['id']}/treatments", json={"medication": "Бипин", "next_treatment_date": TODAY.isoformat()},
                headers=people["keeper"])
    night = datetime(TODAY.year, TODAY.month, TODAY.day, 23, 30, tzinfo=app_zone())
    assert run(db, night) == ({"status": "quiet", "sent": 0, "failed": 0, "left": 0}, [])


def test_in_tajik_for_tajik_users(client, db, people, hive):
    client.put("/api/auth/me/language", json={"language": "tg"}, headers=people["keeper"])
    client.post(f"/api/hives/{hive['id']}/treatments", json={"medication": "Бипин", "next_treatment_date": TODAY.isoformat()},
                headers=people["keeper"])
    _, sent = run(db)
    tg = next((t, b) for c, t, b in sent if c == 3000)
    ru = next((t, b) for c, t, b in sent if c == 1000)
    assert "Қуттии №27" in tg[0] and "Имрӯз" in tg[0] and tg[1][0] == "Кушодани қуттӣ"
    assert "Улей №27" in ru[0]


def test_people_without_telegram_are_skipped(client, db, people, hive, login):
    acc = client.post("/api/admin/accounts", json={"first_name": "Азиз", "login": "aziz", "role": "BEEKEEPER"},
                      headers=people["admin"])
    assert acc.status_code == 201
    client.post(f"/api/hives/{hive['id']}/treatments", json={"medication": "Бипин", "next_treatment_date": TODAY.isoformat()},
                headers=people["keeper"])
    assert chats(run(db)[1]) == [1000, 3000, 4001]


def test_dispatch_endpoint_is_for_the_bot_only(client, people, hive, outbox, monkeypatch):
    monkeypatch.setattr(get_settings(), "notify_from_hour", 0)
    monkeypatch.setattr(get_settings(), "notify_to_hour", 24)
    client.post(f"/api/hives/{hive['id']}/treatments", json={"medication": "Бипин", "next_treatment_date": TODAY.isoformat()},
                headers=people["keeper"])
    assert client.post("/api/notifications/dispatch").status_code == 403
    assert client.post("/api/notifications/dispatch", headers=people["admin"]).status_code == 403
    r = client.post("/api/notifications/dispatch", headers=BOT)
    assert r.status_code == 200 and r.json()["sent"] == 3 and len(outbox) == 3


def test_settings_and_test_message(client, people, outbox, db):
    s = client.get("/api/notifications/settings", headers=people["assistant"]).json()
    assert s == {"field": True, "crm": True, "crm_available": False, "telegram": True, "hours": "7:00–21:00"}
    r = client.put("/api/notifications/settings", json={"crm": False}, headers=people["keeper"])
    assert r.json()["crm"] is False and r.json()["field"] is True and r.json()["crm_available"] is True
    assert client.post("/api/notifications/test", headers=people["keeper"]).json() == {"sent": True}
    assert outbox[0][0] == 3000 and outbox[0][1].startswith("🔔 Уведомления Fayzi Umar работают.")


def test_test_message_needs_telegram(client, people, monkeypatch):
    acc = client.post("/api/admin/accounts", json={"first_name": "Азиз", "login": "aziz", "role": "VIEWER"},
                      headers=people["admin"]).json()
    body = client.post("/api/auth/password", json={"login": "aziz", "password": acc["temporary_password"]}).json()
    h = {"Authorization": f"Bearer {body['access_token']}"}
    client.put("/api/auth/me/password", json={"current_password": acc["temporary_password"], "new_password": "pchela-2026"},
               headers=h)
    r = client.post("/api/notifications/test", headers=h)
    assert r.status_code == 409 and "только в Telegram" in r.json()["detail"]
    assert client.get("/api/notifications/settings", headers=h).json()["telegram"] is False
