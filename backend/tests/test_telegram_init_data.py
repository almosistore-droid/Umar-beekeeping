"""Unit tests for Telegram initData signature validation."""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl, urlencode

import pytest

from app.auth.telegram import InitDataError, sign_init_data, validate_init_data

TOKEN = "7000000000:TEST-token-for-unit-tests"


def _fields(**over):
    f = {
        "user": json.dumps({"id": 42, "first_name": "Анна", "username": "anna"}, ensure_ascii=False),
        "auth_date": str(int(time.time())),
        "query_id": "q1",
    }
    f.update(over)
    return f


def test_valid_init_data_is_accepted():
    data = validate_init_data(sign_init_data(_fields(start_param="hive_abc"), TOKEN), TOKEN)
    assert data.user.id == 42
    assert data.user.first_name == "Анна"
    assert data.start_param == "hive_abc"


def test_reference_algorithm_matches_telegram_spec():
    """Independently re-implement the documented algorithm to guard against regressions."""
    fields = _fields()
    dcs = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    h = hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()
    raw = urlencode({**fields, "hash": h})
    assert validate_init_data(raw, TOKEN).user.id == 42


def test_tampered_user_id_is_rejected():
    raw = sign_init_data(_fields(), TOKEN)
    pairs = dict(parse_qsl(raw))
    pairs["user"] = pairs["user"].replace('"id":42', '"id":1000').replace('"id": 42', '"id": 1000')
    with pytest.raises(InitDataError, match="signature"):
        validate_init_data(urlencode(pairs), TOKEN)


def test_wrong_bot_token_is_rejected():
    raw = sign_init_data(_fields(), "999:other-bot")
    with pytest.raises(InitDataError, match="signature"):
        validate_init_data(raw, TOKEN)


def test_missing_hash_is_rejected():
    with pytest.raises(InitDataError, match="hash"):
        validate_init_data(urlencode(_fields()), TOKEN)


def test_expired_init_data_is_rejected():
    raw = sign_init_data(_fields(auth_date=str(int(time.time()) - 90000)), TOKEN)
    with pytest.raises(InitDataError, match="expired"):
        validate_init_data(raw, TOKEN, max_age_seconds=86400)


def test_future_auth_date_is_rejected():
    raw = sign_init_data(_fields(auth_date=str(int(time.time()) + 3600)), TOKEN)
    with pytest.raises(InitDataError, match="future"):
        validate_init_data(raw, TOKEN)


def test_duplicate_keys_are_rejected():
    raw = sign_init_data(_fields(), TOKEN) + "&user=%7B%22id%22%3A1%7D"
    with pytest.raises(InitDataError):
        validate_init_data(raw, TOKEN)


@pytest.mark.parametrize("raw", ["", "not a query string", "hash="])
def test_garbage_is_rejected(raw):
    with pytest.raises(InitDataError):
        validate_init_data(raw, TOKEN)


def test_empty_bot_token_never_validates():
    with pytest.raises(InitDataError, match="not configured"):
        validate_init_data(sign_init_data(_fields(), ""), "")
