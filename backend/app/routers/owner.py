"""Owner API: the subscription owner's panel (deploy/owner) reads statistics and changes the paid-until date.

Reached only from the server's Docker network (the edge nginx does not route /api/owner) and protected by
OWNER_TOKEN, compared in constant time. Works while the client is blocked (see the subscription middleware).
"""
import hmac
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.models import ARCHIVED_HIVE_STATUSES, Apiary, AuditLog, Hive, User
from app.schemas.common import today
from app.services import branding_service, honey_service, subscription_service
from app.utils.errors import NotFoundError, Unauthorized

router = APIRouter(prefix="/api/owner", tags=["owner"], include_in_schema=False)
DB = Annotated[Session, Depends(get_db)]


def require_owner(x_owner_token: Annotated[str | None, Header()] = None) -> Settings:
    settings = get_settings()
    if not settings.owner_token:
        raise NotFoundError("Не найдено")
    if not x_owner_token or not hmac.compare_digest(x_owner_token.encode(), settings.owner_token.encode()):
        raise Unauthorized("Неверный ключ владельца")
    return settings


Owner = Annotated[Settings, Depends(require_owner)]


class SubscriptionIn(BaseModel):
    until: date | None  # None = no limit


def _subscription(settings: Settings) -> dict:
    until = subscription_service.effective_until(settings)
    left = (until - today()).days if until else None
    return {"until": until, "days_left": left, "active": until is None or left >= 0,
            "source": subscription_service.source(settings), "contact": settings.subscription_contact or None}


@router.get("/stats")
def stats(db: DB, settings: Owner) -> dict:
    t = today()
    users_total = db.scalar(select(func.count()).select_from(User)) or 0
    users_active = db.scalar(select(func.count()).select_from(User).where(User.is_active.is_(True))) or 0
    return {
        "brand": {"name": settings.brand_name, "color": settings.brand_color},
        "subscription": _subscription(settings),
        "hives": db.scalar(select(func.count()).select_from(Hive).where(Hive.status.not_in(ARCHIVED_HIVE_STATUSES))) or 0,
        "apiaries": db.scalar(select(func.count()).select_from(Apiary).where(Apiary.is_archived.is_(False))) or 0,
        "users": {"active": users_active, "total": users_total},
        "last_login": db.scalar(select(func.max(User.last_seen_at))),
        "last_change": db.scalar(select(func.max(AuditLog.created_at))),
        "honey_year_kg": honey_service.stats(db, t.year)["year_kg"],
        "schema": db.scalar(text("SELECT version_num FROM alembic_version")),
    }


@router.put("/subscription")
def set_subscription(body: SubscriptionIn, db: DB, settings: Owner) -> dict:
    subscription_service.set_until(db, body.until, "owner panel")
    return {"subscription": _subscription(settings), "blocked": branding_service.is_blocked(settings)}
