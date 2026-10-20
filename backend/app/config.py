"""Application settings. All secrets come from the environment (.env), never from code."""
import re
from datetime import date
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Beekeeping Management System"
    environment: str = Field(default="development", description="development | test | production")

    # Calendar day of the apiary: «today», default dates and report periods follow this zone (IANA name)
    timezone: str = "Asia/Dushanbe"

    database_url: str = "postgresql+psycopg://bee:bee@localhost:5432/beekeeping"

    # Telegram
    telegram_bot_token: str = Field(default="", description="Bot token from @BotFather")
    telegram_bot_username: str = ""
    telegram_webapp_short_name: str = ""
    # initData older than this is rejected (protects against replay of leaked initData)
    telegram_init_data_max_age_seconds: int = 86400
    # App on the phone outside Telegram: login code lifetime and how long an unused device stays logged in
    login_code_ttl_seconds: int = 300
    device_session_idle_days: int = 180
    # Telegram reminders are sent only between these local hours (settings.timezone)
    notify_from_hour: int = 7
    notify_to_hour: int = 21

    # Telegram IDs that get the ADMIN role on first login (comma-separated in env)
    # NoDecode: read "1,2,3" as plain text (split below) instead of expecting JSON
    admin_telegram_ids: Annotated[list[int], NoDecode] = Field(default_factory=list)
    # Role assigned to any other new user
    default_user_role: str = "VIEWER"

    # JWT
    jwt_secret: str = Field(default="", description="Long random string")
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"  # never «none» or a public-key algorithm
    jwt_expire_minutes: int = 60 * 12

    # Money label shown next to amounts (CRM, reports)
    currency: str = "смн"

    # Brand of this installation (each client of the subscription has its own): name, line under it,
    # accent colour and logo file (PNG/WebP/JPEG; empty = the bundled Fayzi Umar logo)
    brand_name: str = "Fayzi Umar"
    brand_subtitle: str = "Учёт пасеки"
    brand_color: str = "#f4c23b"
    brand_logo: str = ""
    # Subscription: after this date (apiary calendar) the app is blocked; empty = no limit
    subscription_until: date | None = None
    # Who to contact to renew (shown on the blocked screen), e.g. «+992 90 000-00-00 · @owner»
    subscription_contact: str = ""
    # Secret shared with the owner panel (deploy/client.sh makes it); empty = the owner API is off
    owner_token: str = ""
    # False: users, roles, passwords and the activity log are managed only from the owner panel
    admin_in_app: bool = True

    @field_validator("owner_token")
    @classmethod
    def _owner_token(cls, v: str) -> str:
        v = v.strip()
        if v and len(v) < 32:
            raise ValueError("OWNER_TOKEN must be at least 32 characters")
        return v

    @field_validator("subscription_until", mode="before")
    @classmethod
    def _empty_date(cls, v):
        return None if isinstance(v, str) and not v.strip() else v

    @field_validator("brand_color")
    @classmethod
    def _hex_colour(cls, v: str) -> str:
        v = v.strip()
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", v):
            raise ValueError("BRAND_COLOR must look like #f4c23b")
        return v.lower()

    # CORS
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["http://localhost:5173"])

    @field_validator("admin_telegram_ids", mode="before")
    @classmethod
    def _split_ids(cls, v):
        if isinstance(v, str):
            return [int(x) for x in v.replace(" ", "").strip("[]").split(",") if x]
        if isinstance(v, int):
            return [v]
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                import json
                return json.loads(v)
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

    @field_validator("default_user_role")
    @classmethod
    def _valid_role(cls, v: str) -> str:
        v = v.upper()
        if v not in {"ADMIN", "BEEKEEPER", "ASSISTANT", "VIEWER"}:
            raise ValueError("default_user_role must be ADMIN, BEEKEEPER, ASSISTANT or VIEWER")
        return v

    def assert_production_ready(self) -> None:
        """Fail fast on startup instead of running with insecure defaults."""
        problems = []
        if not self.telegram_bot_token:
            problems.append("TELEGRAM_BOT_TOKEN is empty")
        if len(self.jwt_secret) < 32:
            problems.append("JWT_SECRET must be at least 32 characters")
        if "sqlite" in self.database_url:
            problems.append("SQLite is not allowed; use PostgreSQL")
        if problems:
            raise RuntimeError("Invalid configuration: " + "; ".join(problems))


@lru_cache
def get_settings() -> Settings:
    return Settings()
