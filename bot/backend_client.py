"""Calls from the bot to the backend (login confirmation), signed with the bot token."""
import logging

import aiohttp

from config import BACKEND_URL, BOT_TOKEN
from signing import bot_signature

log = logging.getLogger(__name__)


async def post(path: str, payload: dict, lang: str = "ru") -> tuple[int, dict]:
    """POST to the backend → (HTTP status, JSON body). Status 0 = backend unreachable."""
    headers = {"X-Bot-Auth": bot_signature(BOT_TOKEN), "X-Lang": lang}
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.post(f"{BACKEND_URL}{path}", json=payload, headers=headers) as resp:
                try:
                    body = await resp.json(content_type=None)
                except ValueError:
                    body = {}
                return resp.status, body if isinstance(body, dict) else {}
    except (aiohttp.ClientError, TimeoutError) as exc:
        log.warning("backend %s unreachable: %s", path, exc)
        return 0, {}
