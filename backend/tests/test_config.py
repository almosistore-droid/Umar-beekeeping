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


@pytest.mark.parametrize(
    "raw, expected",
    [("https://bee.example.com", ["https://bee.example.com"]),
     ("http://a.com, http://b.com", ["http://a.com", "http://b.com"]),
     ('["http://a.com"]', ["http://a.com"])],
)
def test_cors_origins_from_environment(monkeypatch, raw, expected):
    # Regression: plain-text env values used to crash the server on startup
    monkeypatch.setenv("CORS_ORIGINS", raw)
    assert Settings(_env_file=None).cors_origins == expected


@pytest.mark.parametrize("raw, expected", [("111111", [111111]), ("1, 2,3", [1, 2, 3]), ("", [])])
def test_admin_ids_from_environment(monkeypatch, raw, expected):
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", raw)
    assert Settings(_env_file=None).admin_telegram_ids == expected


def test_dev_compose_environment_loads(monkeypatch):
    """The exact values docker-compose.dev.yml passes must load."""
    for k, v in {"ENVIRONMENT": "development", "CORS_ORIGINS": "http://localhost:5173",
                 "ADMIN_TELEGRAM_IDS": "111111", "DEFAULT_USER_ROLE": "VIEWER",
                 "TELEGRAM_INIT_DATA_MAX_AGE_SECONDS": "604800"}.items():
        monkeypatch.setenv(k, v)
    s = Settings(_env_file=None)
    assert s.cors_origins == ["http://localhost:5173"] and s.admin_telegram_ids == [111111]


def test_apiary_calendar_day_follows_timezone(monkeypatch):
    """At 00:30 in Dushanbe (19:30 UTC the day before) the apiary's date is already the next day."""
    from datetime import date, datetime, timezone

    from app.config import get_settings
    from app.schemas.common import local_date

    monkeypatch.setattr(get_settings(), "timezone", "Asia/Dushanbe")
    assert local_date(datetime(2026, 10, 13, 19, 30, tzinfo=timezone.utc)) == date(2026, 10, 14)
    assert local_date(datetime(2026, 10, 13, 18, 59, tzinfo=timezone.utc)) == date(2026, 10, 13)
    monkeypatch.setattr(get_settings(), "timezone", "UTC")
    assert local_date(datetime(2026, 10, 13, 19, 30, tzinfo=timezone.utc)) == date(2026, 10, 13)
