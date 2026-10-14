import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.auth.jwt import create_access_token
from app.auth.telegram import InitDataError, validate_init_data
from app.config import get_settings
from app.database import get_db
from app.schemas.auth import AuthResponse, LanguageUpdate, TelegramAuthRequest, UserOut
from app.services.auth_service import upsert_telegram_user

router = APIRouter(prefix="/api/auth", tags=["auth"])
log = logging.getLogger(__name__)

# Default placeholder from docker-compose.dev.yml: means .env was not picked up
DEV_PLACEHOLDER_TOKEN_SUFFIX = "local-test-token"


def signature_hint(bot_token: str) -> str:
    """Explain a signature mismatch without revealing the secret part of the token.

    The part before ':' is the bot's numeric id: public, safe to show, and enough
    for the owner to compare with the token in @BotFather.
    """
    if bot_token.endswith(DEV_PLACEHOLDER_TOKEN_SUFFIX):
        return (" Сервер работает с тестовым токеном: файл .env в корне проекта не найден или в нём"
                " нет TELEGRAM_BOT_TOKEN. Впишите токен бота и перезапустите backend.")
    bot_id = bot_token.split(":", 1)[0]
    return (f" Сервер настроен на бота с номером {bot_id}. Проверьте в @BotFather → API Token,"
            " что токен этого бота начинается с того же номера, и откройте приложение из этого бота.")


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
        detail = f"Не удалось подтвердить вход через Telegram: {exc}."
        if "signature" in str(exc):
            log.warning("Telegram initData signature mismatch (server bot id %s)",
                        settings.telegram_bot_token.split(":", 1)[0])
            if settings.environment != "production":
                detail += signature_hint(settings.telegram_bot_token)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail) from None

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


@router.put("/me/language", response_model=UserOut)
def set_language(body: LanguageUpdate, user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    """Language chosen in «Ещё → Язык · Забон»; also used for bot messages."""
    user.language = body.language
    db.commit()
    db.refresh(user)
    return user
