import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import UserRole


class TelegramAuthRequest(BaseModel):
    init_data: str = Field(min_length=1, max_length=8192, description="Raw Telegram.WebApp.initData")


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    display_name: str
    role: UserRole
    is_active: bool
    last_seen_at: datetime | None = None
    language: str | None = None
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut
    start_param: str | None = None


class LanguageUpdate(BaseModel):
    language: Literal["ru", "tg"]


# ---------- app on the phone outside Telegram (login confirmed in the bot) ----------

class LoginCodeRequest(BaseModel):
    device_name: str | None = Field(default=None, max_length=120, description="e.g. «iPhone · Safari»")


class LoginCodeOut(BaseModel):
    code: str
    poll_secret: str
    bot_link: str
    bot_username: str
    expires_in: int


_CODE = Field(min_length=16, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class LoginPollRequest(BaseModel):
    code: str = _CODE
    poll_secret: str = Field(min_length=16, max_length=128)


class LoginPollOut(BaseModel):
    status: Literal["pending", "denied", "expired", "ok"]
    access_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None
    device_token: str | None = None
    user: UserOut | None = None


class BotTelegramUser(BaseModel):
    id: int = Field(gt=0)
    first_name: str | None = Field(default=None, max_length=128)
    last_name: str | None = Field(default=None, max_length=128)
    username: str | None = Field(default=None, max_length=64)
    language_code: str | None = Field(default=None, max_length=16)


class BotConfirmRequest(BaseModel):
    code: str = _CODE
    user: BotTelegramUser


class BotDenyRequest(BaseModel):
    code: str = _CODE


class BotConfirmOut(BaseModel):
    display_name: str
    language: str | None


class DeviceTokenRequest(BaseModel):
    device_token: str = Field(min_length=16, max_length=128)
