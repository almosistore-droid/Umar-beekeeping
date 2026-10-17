"""Stage 8: Telegram reminders — settings of the current person, a test message, and the bot's trigger."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.config import get_settings
from app.database import get_db
from app.models import User, UserRole
from app.routers.auth import require_bot
from app.schemas.notification import DispatchOut, NotificationSettings, NotificationSettingsUpdate
from app.services import notification_service

router = APIRouter(prefix="/api/notifications", tags=["notifications"])
DB = Annotated[Session, Depends(get_db)]


def _settings_out(user: User) -> NotificationSettings:
    s = get_settings()
    return NotificationSettings(field=user.notify_field, crm=user.notify_crm,
                                crm_available=user.role in (UserRole.ADMIN, UserRole.BEEKEEPER),
                                telegram=user.telegram_id is not None,
                                hours=f"{s.notify_from_hour}:00–{s.notify_to_hour}:00")


@router.get("/settings", response_model=NotificationSettings)
def get_settings_(user: CurrentUser):
    return _settings_out(user)


@router.put("/settings", response_model=NotificationSettings)
def update_settings(body: NotificationSettingsUpdate, user: CurrentUser, db: DB):
    if body.field is not None:
        user.notify_field = body.field
    if body.crm is not None:
        user.notify_crm = body.crm
    db.commit()
    db.refresh(user)
    return _settings_out(user)


@router.post("/test")
def send_test(user: CurrentUser):
    notification_service.send_test(user)
    return {"sent": True}


@router.post("/dispatch", response_model=DispatchOut, dependencies=[Depends(require_bot)])
def dispatch(db: DB):
    """Called by our bot every few minutes: sends reminders that are due and not sent yet."""
    return notification_service.dispatch(db, get_settings())
