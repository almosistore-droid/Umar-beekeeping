"""Application settings. All secrets come from the environment (.env), never from code."""
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Beekeeping Management System"
    environment: str = Field(default="development", description="development | test | production")

    database_url: str = "postgresql+psycopg://bee:bee@localhost:5432/beekeeping"

    # Telegram
    telegram_bot_token: str = Field(default="", description="Bot token from @BotFather")
    telegram_bot_username: str = ""
    telegram_webapp_short_name: str = ""
    # initData older than this is rejected (protects against replay of leaked initData)
    telegram_init_data_max_age_seconds: int = 86400

    # Telegram IDs that get the ADMIN role on first login (comma-separated in env)
    admin_telegram_ids: list[int] = Field(default_factory=list)
    # Role assigned to any other new user
    default_user_role: str = "VIEWER"

    # JWT
    jwt_secret: str = Field(default="", description="Long random string")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12

    # CORS
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    @field_validator("admin_telegram_ids", mode="before")
    @classmethod
    def _split_ids(cls, v):
        if isinstance(v, str):
            return [int(x) for x in v.replace(" ", "").split(",") if x]
        if isinstance(v, int):
            return [v]
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
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
