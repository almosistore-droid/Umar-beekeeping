from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.auth.jwt import create_access_token
from app.auth.telegram import InitDataError, validate_init_data
from app.config import get_settings
from app.database import get_db
from app.schemas.auth import AuthResponse, TelegramAuthRequest, UserOut
from app.services.auth_service import upsert_telegram_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/telegram", response_model=AuthResponse)
def telegram_login(body: TelegramAuthRequest, db: Annotated[Session, Depends(get_db)]):
    """Exchange signed Telegram initData for an API access token."""
    settings = get_settings()
    try:
        data = validate_init_data(
            body.init_data,
            settings.telegram_bot_token,
            max_age_seconds=settings.telegram_init_data_max_age_seconds,
        )
    except InitDataError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, f"Не удалось подтвердить вход через Telegram: {exc}"
        ) from None

    user = upsert_telegram_user(db, data.user, settings)
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Учётная запись отключена")

    token, expires_in = create_access_token(user.id, user.role.value)
    return AuthResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserOut.model_validate(user),
        start_param=data.start_param,
    )


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user
