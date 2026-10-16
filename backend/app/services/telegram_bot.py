"""Outgoing Telegram Bot API calls made by the backend (stage 8 notifications will reuse this)."""
import httpx

from app.config import get_settings
from app.utils.errors import ConflictError, DomainError


class TelegramUnavailable(DomainError):
    status_code = 502


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
