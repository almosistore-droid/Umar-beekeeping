"""Proof that a request comes from our own bot: HMAC of a fixed label keyed with the bot token.

Both the bot and the backend know the token, so no extra secret is needed. The same function lives in
bot/signing.py (the bot image does not contain the backend); tests check that both give the same value.
"""
import hashlib
import hmac

LABEL = b"fayzi-umar:bot-login:v1"


def bot_signature(bot_token: str) -> str:
    return hmac.new(bot_token.encode(), LABEL, hashlib.sha256).hexdigest()


def is_valid_bot_signature(value: str | None, bot_token: str) -> bool:
    return bool(bot_token and value) and hmac.compare_digest(value, bot_signature(bot_token))
