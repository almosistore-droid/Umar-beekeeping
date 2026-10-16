import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.auth.bot_signature import is_valid_bot_signature
from app.auth.jwt import create_access_token
from app.auth.telegram import InitDataError, TelegramUser, validate_init_data
from app.config import get_settings
from app.database import get_db
from app.schemas.auth import (
    AuthResponse,
    BotConfirmOut,
    BotConfirmRequest,
    BotDenyRequest,
    DeviceTokenRequest,
    LanguageUpdate,
    LoginCodeOut,
    LoginCodeRequest,
    LoginPollOut,
    LoginPollRequest,
    PasswordChange,
    PasswordLoginRequest,
    TelegramAuthRequest,
    UserOut,
)
from app.services import device_auth_service as device_auth
from app.services import password_service
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


# ---------- app on the phone outside Telegram: login confirmed in the bot ----------

@router.post("/login-codes", response_model=LoginCodeOut, status_code=201)
def create_login_code(body: LoginCodeRequest, db: Annotated[Session, Depends(get_db)]):
    """Start a login: the app opens `bot_link`, the user taps «Войти» in the bot, the app polls."""
    settings = get_settings()
    code, poll_secret, ttl = device_auth.create_code(db, settings, body.device_name)
    return LoginCodeOut(code=code, poll_secret=poll_secret, bot_link=device_auth.bot_link(settings, code),
                        bot_username=settings.telegram_bot_username.lstrip("@"), expires_in=ttl)


@router.post("/login-codes/poll", response_model=LoginPollOut)
def poll_login_code(body: LoginPollRequest, db: Annotated[Session, Depends(get_db)]):
    result = device_auth.poll(db, get_settings(), body.code, body.poll_secret)
    if result["status"] == "ok":
        result["user"] = UserOut.model_validate(result["user"])
    return LoginPollOut(**result)


def require_bot(x_bot_auth: Annotated[str | None, Header()] = None) -> None:
    if not is_valid_bot_signature(x_bot_auth, get_settings().telegram_bot_token):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Только для бота")


@router.post("/login-codes/confirm", response_model=BotConfirmOut, dependencies=[Depends(require_bot)])
def confirm_login_code(body: BotConfirmRequest, db: Annotated[Session, Depends(get_db)]):
    """Called by our bot when the user taps «Войти»; the Telegram user comes from Telegram's own update."""
    tg = TelegramUser(**body.user.model_dump())
    user = device_auth.confirm(db, get_settings(), body.code, tg)
    return BotConfirmOut(display_name=user.display_name, language=user.language)


@router.post("/login-codes/deny", status_code=204, dependencies=[Depends(require_bot)])
def deny_login_code(body: BotDenyRequest, db: Annotated[Session, Depends(get_db)]):
    device_auth.deny(db, body.code)
    return Response(status_code=204)


@router.post("/device", response_model=AuthResponse)
def device_login(body: DeviceTokenRequest, db: Annotated[Session, Depends(get_db)]):
    """Next launch on a logged-in phone: device token → access token."""
    user = device_auth.exchange(db, get_settings(), body.device_token)
    token, expires_in = create_access_token(user.id, user.role.value)
    return AuthResponse(access_token=token, expires_in=expires_in, user=UserOut.model_validate(user))


@router.post("/logout", status_code=204)
def logout(body: DeviceTokenRequest, db: Annotated[Session, Depends(get_db)]):
    """«Выйти» on the phone: this device token stops working."""
    device_auth.revoke(db, body.device_token)
    return Response(status_code=204)


# ---------- login and password (people without Telegram) ----------

@router.post("/password", response_model=LoginPollOut)
def password_login(body: PasswordLoginRequest, db: Annotated[Session, Depends(get_db)]):
    """Login + password → access token and a device token (the phone stays logged in)."""
    result = password_service.login_with_password(db, body.login, body.password, body.device_name)
    result["user"] = UserOut.model_validate(result["user"])
    return LoginPollOut(**result)


@router.put("/me/password", response_model=UserOut)
def change_password(body: PasswordChange, user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    return password_service.change_password(db, user, body.current_password, body.new_password)
