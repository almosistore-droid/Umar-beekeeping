import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import ADMIN_ONLY, require_roles
from app.database import get_db
from app.models import User, UserRole
from app.schemas.auth import UserOut
from app.schemas.user import UserUpdate
from app.services import audit_service as audit
from app.utils.errors import ConflictError, NotFoundError

router = APIRouter(prefix="/api/users", tags=["users"])
DB = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(require_roles(*ADMIN_ONLY))]


@router.get("", response_model=list[UserOut])
def list_users(db: DB, _: Admin):
    return db.scalars(select(User).order_by(User.created_at)).all()


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: uuid.UUID, body: UserUpdate, db: DB, admin: Admin):
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("Пользователь не найден")
    changes = body.model_dump(exclude_unset=True)
    if user.id == admin.id and (changes.get("role", UserRole.ADMIN) != UserRole.ADMIN or changes.get("is_active") is False):
        raise ConflictError("Нельзя снять права администратора или отключить самого себя")
    before = audit.snapshot(user, ["role", "is_active"])
    for key, value in changes.items():
        setattr(user, key, value)
    old, new = audit.diff(before, audit.snapshot(user, ["role", "is_active"]))
    if new:
        audit.record(db, user=admin, entity_type="user", entity_id=user.id, action="updated", old=old, new=new)
    db.commit()
    db.refresh(user)
    return user
