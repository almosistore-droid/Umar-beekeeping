"""Outgoing Telegram Bot API calls made by the backend: files to a user's chat, reminders (stage 8)."""
import httpx

from app.config import get_settings
from app.utils.errors import ConflictError, DomainError


class TelegramUnavailable(DomainError):
    status_code = 502


class TelegramBlocked(DomainError):
    """The person blocked the bot or never pressed Start: retrying will not help."""
    status_code = 409


_PERMANENT = ("blocked", "chat not found", "user is deactivated", "bot can't initiate", "have no rights")


def send_message(chat_id: int, text: str, button: tuple[str, str] | None = None) -> None:
    """Send a text message; `button` = (label, url) shown under it."""
    token = get_settings().telegram_bot_token
    if not token:
        raise TelegramUnavailable("Бот не настроен (нет TELEGRAM_BOT_TOKEN)")
    payload: dict = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if button:
        payload["reply_markup"] = {"inline_keyboard": [[{"text": button[0], "url": button[1]}]]}
    try:
        response = httpx.post(f"https://api.telegram.org/bot{token}/sendMessage", json=payload, timeout=15)
        body = response.json()
    except (httpx.HTTPError, ValueError):
        raise TelegramUnavailable("Telegram не отвечает") from None
    if response.status_code == 200 and body.get("ok"):
        return
    description = str(body.get("description", "")).lower()
    if response.status_code in (400, 403) and any(p in description for p in _PERMANENT):
        raise TelegramBlocked("Человек заблокировал бота или ни разу не нажимал «Start»")
    raise TelegramUnavailable("Telegram не принял сообщение")


def send_document(chat_id: int | None, filename: str, content: bytes, caption: str | None = None,
                  media_type: str = "application/pdf") -> None:
    if chat_id is None:
        raise ConflictError("У вас нет Telegram в профиле — скачайте файл кнопкой «Скачать»")
    token = get_settings().telegram_bot_token
    if not token:
        raise ConflictError("Бот не настроен (нет TELEGRAM_BOT_TOKEN) — скачайте файл в браузере")
    try:
        response = httpx.post(
            f"https://api.telegram.org/bot{token}/sendDocument",
            data={"chat_id": str(chat_id), **({"caption": caption} if caption else {})},
            files={"document": (filename, content, media_type)},
            timeout=30,
        )
        ok = response.status_code == 200 and response.json().get("ok")
    except (httpx.HTTPError, ValueError):
        ok = False
    if not ok:
        raise TelegramUnavailable(
            "Telegram не принял файл. Откройте чат с ботом и нажмите «Start», затем попробуйте снова."
        )
