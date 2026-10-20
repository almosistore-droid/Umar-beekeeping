import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import ADMIN_ONLY, require_admin_in_app, require_roles
from app.database import get_db
from app.models import User
from app.schemas.auth import UserOut
from app.schemas.user import UserUpdate
from app.services import admin_service

router = APIRouter(prefix="/api/users", tags=["users"], dependencies=[Depends(require_admin_in_app)])
DB = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(require_roles(*ADMIN_ONLY))]


@router.get("", response_model=list[UserOut])
def list_users(db: DB, _: Admin):
    return admin_service.list_users(db)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: uuid.UUID, body: UserUpdate, db: DB, admin: Admin):
    return admin_service.update_user(db, user_id, body.model_dump(exclude_unset=True), admin)
