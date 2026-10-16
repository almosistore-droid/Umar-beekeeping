"""Header that proves a request to the backend comes from this bot (copy of backend app/auth/bot_signature.py)."""
import hashlib
import hmac

LABEL = b"fayzi-umar:bot-login:v1"


def bot_signature(bot_token: str) -> str:
    return hmac.new(bot_token.encode(), LABEL, hashlib.sha256).hexdigest()
