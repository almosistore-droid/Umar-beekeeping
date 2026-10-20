import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import ADMIN_ONLY, require_admin_in_app, require_roles
from app.database import get_db
from app.models import User
from app.schemas.admin import (
    AccountCreate,
    AccountCredentials,
    AuditPage,
    InviteCreate,
    InviteOut,
    InviteResult,
    OverviewOut,
    PasswordReset,
)
from app.schemas.auth import UserOut
from app.services import admin_service, password_service

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin_in_app)])
DB = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(require_roles(*ADMIN_ONLY))]


@router.get("/overview", response_model=OverviewOut)
def overview(db: DB, _: Admin):
    """Everything about the Mini App on one screen."""
    return admin_service.overview(db)


@router.get("/invites", response_model=list[InviteOut])
def list_invites(db: DB, _: Admin):
    return admin_service.list_invites(db)


@router.post("/invites", response_model=InviteResult, status_code=status.HTTP_201_CREATED)
def create_invite(body: InviteCreate, db: DB, admin: Admin):
    """Add a person in advance. If they already use the app, their role is changed at once."""
    return admin_service.create_invite(db, body, admin)


@router.post("/invites/{invite_id}/revoke", response_model=InviteOut)
def revoke_invite(invite_id: uuid.UUID, db: DB, admin: Admin):
    return admin_service.revoke_invite(db, invite_id, admin)


@router.get("/audit", response_model=AuditPage)
def audit_log(db: DB, _: Admin, user_id: uuid.UUID | None = None,
              entity_type: Annotated[str | None, Query(max_length=40)] = None,
              offset: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=200)] = 50):
    return admin_service.audit_log(db, user_id=user_id, entity_type=entity_type, offset=offset, limit=limit)


@router.post("/accounts", response_model=AccountCredentials, status_code=status.HTTP_201_CREATED)
def create_account(body: AccountCreate, db: DB, admin: Admin):
    """A person without Telegram: login + temporary password, changed at the first login."""
    user, password = password_service.create_account(db, admin, first_name=body.first_name, last_name=body.last_name,
                                                     login=body.login, role=body.role)
    return AccountCredentials(user=UserOut.model_validate(user), login=user.login, temporary_password=password)


@router.post("/users/{user_id}/password", response_model=AccountCredentials)
def reset_password(user_id: uuid.UUID, body: PasswordReset, db: DB, admin: Admin):
    """New temporary password (or a first login for a Telegram user); the person is logged out everywhere."""
    user, password = password_service.reset_password(db, admin, user_id, body.login)
    return AccountCredentials(user=UserOut.model_validate(user), login=user.login, temporary_password=password)
