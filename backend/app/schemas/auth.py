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
