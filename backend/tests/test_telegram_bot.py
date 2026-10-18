"""Outgoing Bot API calls: success, a person who blocked the bot (do not retry), Telegram down (retry later)."""
import httpx
import pytest

from app.config import get_settings
from app.services import telegram_bot as tb
from app.utils.errors import ConflictError


@pytest.fixture
def telegram(monkeypatch):
    calls = []

    def install(status=200, body=None, exc=None):
        def fake_post(url, **kw):
            calls.append((url, kw))
            if exc:
                raise exc
            return httpx.Response(status, json=body if body is not None else {"ok": True})
        monkeypatch.setattr(tb.httpx, "post", fake_post)
        return calls
    return install


def test_message_with_button(telegram):
    calls = telegram()
    tb.send_message(42, "Привет", ("Открыть улей", "https://t.me/bot?startapp=hive_1"))
    url, kw = calls[0]
    assert url.endswith("/sendMessage") and kw["json"]["chat_id"] == 42
    assert kw["json"]["reply_markup"]["inline_keyboard"][0][0]["text"] == "Открыть улей"


def test_blocked_person_is_permanent(telegram):
    telegram(403, {"ok": False, "description": "Forbidden: bot was blocked by the user"})
    with pytest.raises(tb.TelegramBlocked):
        tb.send_message(42, "x")


@pytest.mark.parametrize("kw", [{"status": 500, "body": {"ok": False}}, {"exc": httpx.ConnectError("down")},
                                {"status": 400, "body": {"ok": False, "description": "Bad Request: message is too long"}}])
def test_telegram_problem_is_retried_later(telegram, kw):
    telegram(**kw)
    with pytest.raises(tb.TelegramUnavailable):
        tb.send_message(42, "x")


def test_no_token(monkeypatch):
    monkeypatch.setattr(get_settings(), "telegram_bot_token", "")
    with pytest.raises(tb.TelegramUnavailable):
        tb.send_message(42, "x")
    with pytest.raises(ConflictError):
        tb.send_document(42, "a.pdf", b"%PDF")


def test_document(telegram):
    calls = telegram()
    tb.send_document(42, "report.pdf", b"%PDF-1.4", caption="Отчёт")
    url, kw = calls[0]
    assert url.endswith("/sendDocument") and kw["data"] == {"chat_id": "42", "caption": "Отчёт"}
    assert kw["files"]["document"][0] == "report.pdf"
    with pytest.raises(ConflictError):
        tb.send_document(None, "a.pdf", b"x")


def test_document_refused(telegram):
    telegram(400, {"ok": False})
    with pytest.raises(tb.TelegramUnavailable):
        tb.send_document(42, "a.pdf", b"x")
