import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import ADMIN_ONLY, require_roles
from app.database import get_db
from app.models import User
from app.schemas.admin import AuditPage, InviteCreate, InviteOut, InviteResult, OverviewOut
from app.services import admin_service

router = APIRouter(prefix="/api/admin", tags=["admin"])
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
