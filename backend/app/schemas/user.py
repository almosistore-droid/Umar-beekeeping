from pydantic import BaseModel

from app.models.user import UserRole


class UserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None
