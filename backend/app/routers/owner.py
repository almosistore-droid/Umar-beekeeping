"""Owner API: the subscription owner's panel (deploy/owner) reads statistics, changes the paid-until date and —
when the owner keeps it for themselves (`admin_in_app` off) — manages the client's users, invitations, passwords
and reads the activity log. Actions are audited without a user (comment «Панель владельца»).

Reached only from the server's Docker network (the edge nginx does not route /api/owner) and protected by
OWNER_TOKEN, compared in constant time. Works while the client is blocked (see the subscription middleware).
"""
import hmac
import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.models import ARCHIVED_HIVE_STATUSES, Apiary, AuditLog, Hive, User
from app.schemas.common import today
from app.schemas.admin import AccountCreate, AccountCredentials, AuditPage, InviteCreate, InviteOut, InviteResult, PasswordReset
from app.schemas.auth import UserOut
from app.schemas.user import UserUpdate
from app.services import admin_service, branding_service, honey_service, password_service, subscription_service
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
        "admin_in_app": subscription_service.admin_in_app(settings),
    }


@router.put("/subscription")
def set_subscription(body: SubscriptionIn, db: DB, settings: Owner) -> dict:
    subscription_service.set_until(db, body.until, "owner panel")
    return {"subscription": _subscription(settings), "blocked": branding_service.is_blocked(settings)}


class SettingsIn(BaseModel):
    admin_in_app: bool


@router.put("/settings")
def set_settings(body: SettingsIn, db: DB, settings: Owner) -> dict:
    """Where users are managed: in the app by the client's admin, or only here."""
    subscription_service.set_admin_in_app(db, body.admin_in_app)
    return {"admin_in_app": subscription_service.admin_in_app(settings)}


# ---------- users (the same rules as the in-app admin panel) ----------

class UsersOut(BaseModel):
    users: list[UserOut]
    invites: list[InviteOut]


@router.get("/users", response_model=UsersOut)
def users(db: DB, _: Owner):
    return UsersOut(users=[UserOut.model_validate(u) for u in admin_service.list_users(db)],
                    invites=admin_service.list_invites(db))


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: uuid.UUID, body: UserUpdate, db: DB, _: Owner):
    return admin_service.update_user(db, user_id, body.model_dump(exclude_unset=True, exclude_none=True), None)


@router.post("/users/{user_id}/password", response_model=AccountCredentials)
def reset_password(user_id: uuid.UUID, body: PasswordReset, db: DB, _: Owner):
    user, password = password_service.reset_password(db, None, user_id, body.login)
    return AccountCredentials(user=UserOut.model_validate(user), login=user.login, temporary_password=password)


@router.post("/accounts", response_model=AccountCredentials, status_code=status.HTTP_201_CREATED)
def create_account(body: AccountCreate, db: DB, _: Owner):
    user, password = password_service.create_account(db, None, first_name=body.first_name, last_name=body.last_name,
                                                     login=body.login, role=body.role)
    return AccountCredentials(user=UserOut.model_validate(user), login=user.login, temporary_password=password)


@router.post("/invites", response_model=InviteResult, status_code=status.HTTP_201_CREATED)
def create_invite(body: InviteCreate, db: DB, _: Owner):
    return admin_service.create_invite(db, body, None)


@router.post("/invites/{invite_id}/revoke", response_model=InviteOut)
def revoke_invite(invite_id: uuid.UUID, db: DB, _: Owner):
    return admin_service.revoke_invite(db, invite_id, None)


@router.get("/audit", response_model=AuditPage)
def audit_log(db: DB, _: Owner, user_id: uuid.UUID | None = None,
              entity_type: Annotated[str | None, Query(max_length=40)] = None,
              offset: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=200)] = 50):
    return admin_service.audit_log(db, user_id=user_id, entity_type=entity_type, offset=offset, limit=limit)
