from typing import Literal

from pydantic import BaseModel


class NotificationSettings(BaseModel):
    field: bool
    crm: bool
    crm_available: bool  # ADMIN / BEEKEEPER
    telegram: bool       # the person has Telegram (otherwise reminders cannot be delivered)
    hours: str           # «7:00–21:00»


class NotificationSettingsUpdate(BaseModel):
    field: bool | None = None
    crm: bool | None = None


class DispatchOut(BaseModel):
    status: Literal["ok", "quiet"]
    sent: int
    failed: int
    left: int
