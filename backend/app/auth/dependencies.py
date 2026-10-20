"""FastAPI dependencies for authentication and role-based access control.

The role is always read from the database, not from the JWT, so a role change or
deactivation takes effect on the next request.
"""
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.jwt import TokenError, decode_access_token
from app.database import get_db
from app.models.user import User, UserRole

bearer = HTTPBearer(auto_error=False)


# Allowed while the temporary password from the admin has not been changed yet
PASSWORD_CHANGE_PATHS = {"/api/auth/me", "/api/auth/me/password", "/api/auth/me/language", "/api/auth/logout"}


def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Требуется авторизация",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = decode_access_token(credentials.credentials)
    except TokenError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Сессия недействительна или истекла",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Пользователь не найден")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Учётная запись отключена")
    if user.must_change_password and request.url.path not in PASSWORD_CHANGE_PATHS:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Сначала смените временный пароль")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    allowed = set(roles)

    def checker(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав для этого действия")
        return user

    return checker


def require_admin_in_app() -> None:
    """User management (users, invitations, passwords, activity log) may be moved to the owner panel."""
    from app.config import get_settings
    from app.services.subscription_service import admin_in_app
    if not admin_in_app(get_settings()):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Управление пользователями доступно только в панели владельца")


# Convenience role groups used by routers
ANY_ROLE = (UserRole.ADMIN, UserRole.BEEKEEPER, UserRole.ASSISTANT, UserRole.VIEWER)
CAN_WRITE = (UserRole.ADMIN, UserRole.BEEKEEPER, UserRole.ASSISTANT)
CAN_MANAGE = (UserRole.ADMIN, UserRole.BEEKEEPER)
ADMIN_ONLY = (UserRole.ADMIN,)
