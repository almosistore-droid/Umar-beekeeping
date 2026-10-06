"""Validation of Telegram Mini App initData.

Spec: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

The client sends the raw ``Telegram.WebApp.initData`` string. We never trust the
user id it contains until the HMAC signature (keyed with our bot token) matches.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode


class InitDataError(ValueError):
    """initData is missing, malformed, forged or expired."""


@dataclass(frozen=True)
class TelegramUser:
    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None


@dataclass(frozen=True)
class ValidatedInitData:
    user: TelegramUser
    auth_date: int
    start_param: str | None
    query_id: str | None


def _secret_key(bot_token: str) -> bytes:
    return hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()


def _data_check_string(fields: dict[str, str]) -> str:
    return "\n".join(f"{k}={fields[k]}" for k in sorted(fields) if k != "hash")


def validate_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int = 86400,
    now: int | None = None,
) -> ValidatedInitData:
    if not bot_token:
        raise InitDataError("Server is not configured with a Telegram bot token")
    if not init_data:
        raise InitDataError("initData is empty")

    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
    except ValueError as exc:
        raise InitDataError("initData is malformed") from exc

    fields = dict(pairs)
    if len(fields) != len(pairs):
        raise InitDataError("initData contains duplicate keys")

    received_hash = fields.get("hash")
    if not received_hash:
        raise InitDataError("initData has no hash")

    expected = hmac.new(
        _secret_key(bot_token), _data_check_string(fields).encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise InitDataError("initData signature is invalid")

    try:
        auth_date = int(fields["auth_date"])
    except (KeyError, ValueError) as exc:
        raise InitDataError("initData has no valid auth_date") from exc

    current = int(time.time()) if now is None else now
    if max_age_seconds > 0 and current - auth_date > max_age_seconds:
        raise InitDataError("initData has expired")
    if auth_date - current > 60:
        raise InitDataError("initData auth_date is in the future")

    try:
        raw_user = json.loads(fields["user"])
        user = TelegramUser(
            id=int(raw_user["id"]),
            first_name=raw_user.get("first_name"),
            last_name=raw_user.get("last_name"),
            username=raw_user.get("username"),
            language_code=raw_user.get("language_code"),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise InitDataError("initData has no valid user") from exc

    return ValidatedInitData(
        user=user,
        auth_date=auth_date,
        start_param=fields.get("start_param"),
        query_id=fields.get("query_id"),
    )


def sign_init_data(fields: dict[str, str], bot_token: str) -> str:
    """Build a correctly signed initData string.

    Used by tests and by the local dev helper (``python -m app.utils.dev_init_data``)
    so the app can be opened in a normal browser without bypassing validation.
    """
    payload = {k: v for k, v in fields.items() if k != "hash"}
    payload["hash"] = hmac.new(
        _secret_key(bot_token), _data_check_string(payload).encode(), hashlib.sha256
    ).hexdigest()
    return urlencode(payload)
