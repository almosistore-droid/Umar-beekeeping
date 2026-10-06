import pytest

from app.config import Settings


def test_admin_ids_parsed_from_csv():
    s = Settings(admin_telegram_ids="1, 2,3", _env_file=None)
    assert s.admin_telegram_ids == [1, 2, 3]


def test_production_rejects_insecure_config():
    s = Settings(environment="production", telegram_bot_token="", jwt_secret="short", _env_file=None)
    with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
        s.assert_production_ready()


def test_production_rejects_sqlite():
    s = Settings(
        environment="production",
        telegram_bot_token="1:x",
        jwt_secret="x" * 40,
        database_url="sqlite:///x.db",
        _env_file=None,
    )
    with pytest.raises(RuntimeError, match="SQLite"):
        s.assert_production_ready()


def test_invalid_default_role_rejected():
    with pytest.raises(ValueError):
        Settings(default_user_role="GOD", _env_file=None)
