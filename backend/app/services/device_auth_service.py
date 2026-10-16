"""Login on a phone outside Telegram, confirmed in the bot.

1. The app asks for a code (`create_code`) and opens `t.me/<bot>?start=login_<code>`.
2. The user taps «Войти» in the bot; the bot calls `confirm` (the bot is the one who knows the real
   Telegram user: the update comes from Telegram's servers, not from the phone).
3. The app polls with the code and its own poll secret (`poll`) and receives a JWT and a device token.
4. Next launches exchange the device token for a JWT (`exchange`); «Выйти» revokes it (`revoke`).
Codes and tokens are random and stored only as SHA-256 hashes.
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.auth.telegram import TelegramUser
from app.config import Settings
from app.models import DeviceSession, LoginCode, LoginCodeStatus, User
from app.services import audit_service as audit
from app.services.auth_service import upsert_telegram_user
from app.utils.errors import ConflictError, Gone, NotConfigured, NotFoundError, PermissionDenied, Unauthorized

START_PREFIX = "login_"
CODE_NOT_FOUND = "Код входа не найден"
CODE_EXPIRED = "Код входа устарел. Нажмите «Войти через Telegram» в приложении ещё раз."
ACCOUNT_DISABLED = "Учётная запись отключена"


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def bot_link(settings: Settings, code: str) -> str:
    return f"https://t.me/{settings.telegram_bot_username.lstrip('@')}?start={START_PREFIX}{code}"


def create_code(db: Session, settings: Settings, device_name: str | None) -> tuple[str, str, int]:
    """New one-time code → (code, poll secret, lifetime in seconds)."""
    if not settings.telegram_bot_username:
        raise NotConfigured("Вход вне Telegram не настроен: на сервере не указан TELEGRAM_BOT_USERNAME")
    code = secrets.token_urlsafe(24)  # 32 characters, fits Telegram's 64-character start parameter
    poll_secret = secrets.token_urlsafe(32)
    ttl = settings.login_code_ttl_seconds
    db.add(LoginCode(code_hash=_hash(code), poll_hash=_hash(poll_secret), device_name=(device_name or None),
                     expires_at=_now() + timedelta(seconds=ttl)))
    db.commit()
    return code, poll_secret, ttl


def _find(db: Session, code: str, lock: bool = False) -> LoginCode | None:
    query = select(LoginCode).where(LoginCode.code_hash == _hash(code))
    return db.scalar(query.with_for_update() if lock else query)


def confirm(db: Session, settings: Settings, code: str, tg: TelegramUser) -> User:
    """«Войти» pressed in the bot by Telegram user `tg`."""
    found = _find(db, code)
    if found is None:
        raise NotFoundError(CODE_NOT_FOUND)
    if found.status != LoginCodeStatus.PENDING:
        raise ConflictError("Этот код уже использован")
    if found.expires_at <= _now():
        raise Gone(CODE_EXPIRED)

    user = upsert_telegram_user(db, tg, settings)  # same account and role as in the Mini App
    if not user.is_active:
        raise PermissionDenied(ACCOUNT_DISABLED)

    found = _find(db, code, lock=True)  # the upsert committed; re-check under a row lock
    if found is None or found.status != LoginCodeStatus.PENDING:
        raise ConflictError("Этот код уже использован")
    found.status = LoginCodeStatus.CONFIRMED
    found.user_id = user.id
    found.confirmed_at = _now()
    db.commit()
    return user


def deny(db: Session, code: str) -> None:
    """«Отмена» pressed in the bot."""
    found = _find(db, code, lock=True)
    if found is None:
        raise NotFoundError(CODE_NOT_FOUND)
    if found.status == LoginCodeStatus.PENDING:
        found.status = LoginCodeStatus.DENIED
        db.commit()


def _issue_device_session(db: Session, user: User, name: str | None) -> str:
    token = secrets.token_urlsafe(32)
    now = _now()
    db.add(DeviceSession(user_id=user.id, token_hash=_hash(token), name=name, last_used_at=now))
    user.last_seen_at = now
    return token


def poll(db: Session, settings: Settings, code: str, poll_secret: str) -> dict:
    """The device asks whether its code was confirmed. Returns {"status": pending|denied|expired|ok, ...}."""
    found = _find(db, code, lock=True)
    if found is None or not hmac.compare_digest(found.poll_hash, _hash(poll_secret)):
        raise NotFoundError(CODE_NOT_FOUND)
    now = _now()
    if found.status == LoginCodeStatus.DENIED:
        return {"status": "denied"}
    if found.status == LoginCodeStatus.USED:
        return {"status": "expired"}
    if found.status == LoginCodeStatus.PENDING:
        return {"status": "expired" if found.expires_at <= now else "pending"}

    # CONFIRMED: collectable for one more lifetime after the code's expiry (the user may come back slowly)
    if found.expires_at + timedelta(seconds=settings.login_code_ttl_seconds) <= now:
        return {"status": "expired"}
    user = db.get(User, found.user_id)
    if user is None or not user.is_active:
        raise PermissionDenied(ACCOUNT_DISABLED)
    device_token = _issue_device_session(db, user, found.device_name)
    found.status = LoginCodeStatus.USED
    found.used_at = now
    audit.record(db, user=user, entity_type="user", entity_id=user.id, action="device_login",
                 new={"device": found.device_name})
    db.commit()
    db.refresh(user)
    access_token, expires_in = create_access_token(user.id, user.role.value)
    return {"status": "ok", "device_token": device_token, "access_token": access_token,
            "expires_in": expires_in, "user": user}


def exchange(db: Session, settings: Settings, device_token: str) -> User:
    """Next launch of the app on a logged-in phone: device token → user (the router issues a JWT)."""
    session = db.scalar(select(DeviceSession).where(DeviceSession.token_hash == _hash(device_token)))
    now = _now()
    idle_limit = now - timedelta(days=settings.device_session_idle_days)
    if session is None or session.revoked_at is not None or session.last_used_at <= idle_limit:
        raise Unauthorized("Вход на этом устройстве больше не действует. Войдите снова.")
    user = session.user
    if not user.is_active:
        raise PermissionDenied(ACCOUNT_DISABLED)
    if user.telegram_id in settings.admin_telegram_ids and user.role.value != "ADMIN":
        # same rule as a login through Telegram: IDs from ADMIN_TELEGRAM_IDS are administrators
        upsert_telegram_user(db, TelegramUser(id=user.telegram_id, first_name=user.first_name,
                                              last_name=user.last_name, username=user.username,
                                              language_code=user.language_code), settings)
    session.last_used_at = now
    user.last_seen_at = now
    db.commit()
    db.refresh(user)
    return user


def revoke(db: Session, device_token: str) -> None:
    """«Выйти» on the phone."""
    session = db.scalar(select(DeviceSession).where(DeviceSession.token_hash == _hash(device_token)))
    if session is not None and session.revoked_at is None:
        session.revoked_at = _now()
        db.commit()
