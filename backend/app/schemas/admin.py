import re
import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.user import InviteStatus, UserRole
from app.schemas.auth import UserOut

_USERNAME = re.compile(r"^[a-z][a-z0-9_]{3,31}$")


class InviteCreate(BaseModel):
    telegram_id: int | None = Field(default=None, gt=0, lt=10**13)
    username: str | None = Field(default=None, max_length=64)
    role: UserRole
    note: str | None = Field(default=None, max_length=200)

    @field_validator("username")
    @classmethod
    def _username(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip().lstrip("@").strip().lower()
        if v.startswith("https://t.me/"):
            v = v.removeprefix("https://t.me/")
        if not v:
            return None
        if not _USERNAME.match(v):
            raise ValueError("Имя пользователя Telegram: 4–32 символа — латинские буквы, цифры и «_»")
        return v

    @field_validator("note")
    @classmethod
    def _note(cls, v: str | None) -> str | None:
        return (v or "").strip() or None

    @model_validator(mode="after")
    def _one_of(self):
        if self.telegram_id is None and self.username is None:
            raise ValueError("Укажите Telegram ID или имя пользователя (@username)")
        return self


class InviteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    telegram_id: int | None
    username: str | None
    role: UserRole
    note: str | None
    status: InviteStatus
    expired: bool
    expires_at: datetime
    created_at: datetime
    created_by_name: str | None
    used_by_name: str | None
    used_at: datetime | None


class InviteResult(BaseModel):
    """Either a new invitation, or — when the person already uses the app — their updated account."""
    kind: Literal["invited", "updated"]
    invite: InviteOut | None = None
    user: UserOut | None = None
    share_text: str | None = None


class SystemInfo(BaseModel):
    environment: str
    timezone: str
    currency: str
    server_time: datetime
    bot_configured: bool
    bot_username: str | None
    deep_links_ready: bool
    database_ok: bool
    database_size_mb: float | None
    migration: str | None


class OverviewOut(BaseModel):
    system: SystemInfo
    users: dict[str, int]
    counts: list["CountRow"]


class CountRow(BaseModel):
    section: str
    label: str
    value: str


class AuditRow(BaseModel):
    id: uuid.UUID
    created_at: datetime
    user_id: uuid.UUID | None
    user_name: str | None
    entity_type: str
    entity_id: uuid.UUID
    hive_id: uuid.UUID | None
    hive_number: str | None
    action: str
    old_value: dict[str, Any] | None
    new_value: dict[str, Any] | None
    comment: str | None


class AuditPage(BaseModel):
    items: list[AuditRow]
    next_offset: int | None
    entity_types: list[str]


OverviewOut.model_rebuild()


class AccountCreate(BaseModel):
    """A person who logs in with a login and password (no Telegram)."""
    first_name: str = Field(min_length=1, max_length=128)
    last_name: str | None = Field(default=None, max_length=128)
    login: str = Field(min_length=1, max_length=64)
    role: UserRole


class PasswordReset(BaseModel):
    login: str | None = Field(default=None, max_length=64, description="Required when the user has no login yet")


class AccountCredentials(BaseModel):
    """Shown to the admin once: the temporary password is not stored anywhere in readable form."""
    user: UserOut
    login: str
    temporary_password: str
