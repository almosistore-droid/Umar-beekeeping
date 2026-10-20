"""Accounts with a login and password, for people who do not use Telegram.

The admin creates the account (or a login for an existing user) and gets a temporary password once;
the person must change it at the first login. Five wrong passwords lock the account for 15 minutes.
"""
import re
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth.jwt import create_access_token
from app.auth.passwords import hash_password, temporary_password, verify_password
from app.models import DeviceSession, User, UserRole
from app.services import audit_service as audit
from app.services.device_auth_service import ACCOUNT_DISABLED, _issue_device_session
from app.utils.errors import (
    ConflictError,
    NotFoundError,
    PermissionDenied,
    TooManyAttempts,
    Unauthorized,
    ValidationFailed,
)

LOGIN_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,31}$")
MAX_FAILED = 5
LOCK_MINUTES = 15
WRONG = "Неверный логин или пароль"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_login(value: str) -> str:
    login = value.strip().lower()
    if not LOGIN_RE.match(login):
        raise ValidationFailed("Логин: 3–32 символа — латинские буквы, цифры, точка, «-» или «_»")
    return login


def check_new_password(password: str, login: str | None) -> None:
    if len(password) < 8:
        raise ValidationFailed("Пароль должен быть не короче 8 символов")
    if len(password) > 128:
        raise ValidationFailed("Пароль слишком длинный")
    if login and password.strip().lower() == login:
        raise ValidationFailed("Пароль не должен совпадать с логином")


def login_with_password(db: Session, login: str, password: str, device_name: str | None) -> dict:
    """Login + password → the same session as a confirmed Telegram login (JWT + device token)."""
    user = db.scalar(select(User).where(User.login == login.strip().lower()).with_for_update())
    now = _now()
    if user is not None and user.locked_until and user.locked_until > now:
        minutes = max(1, int((user.locked_until - now).total_seconds() // 60) + 1)
        raise TooManyAttempts(f"Слишком много неудачных попыток. Попробуйте через {minutes} мин.")
    ok = verify_password(password, user.password_hash if user else None)  # same work for unknown logins
    if user is None or not ok:
        if user is not None:
            user.failed_logins += 1
            if user.failed_logins >= MAX_FAILED:
                user.failed_logins = 0
                user.locked_until = now + timedelta(minutes=LOCK_MINUTES)
                audit.record(db, user=None, entity_type="user", entity_id=user.id, action="login_locked",
                             new={"minutes": LOCK_MINUTES})
            db.commit()
        raise Unauthorized(WRONG)
    if not user.is_active:
        raise PermissionDenied(ACCOUNT_DISABLED)

    user.failed_logins = 0
    user.locked_until = None
    device_token = _issue_device_session(db, user, device_name)
    audit.record(db, user=user, entity_type="user", entity_id=user.id, action="device_login",
                 new={"device": device_name, "method": "password"})
    db.commit()
    db.refresh(user)
    access_token, expires_in = create_access_token(user.id, user.role.value)
    return {"status": "ok", "device_token": device_token, "access_token": access_token,
            "expires_in": expires_in, "user": user}


def change_password(db: Session, user: User, current: str, new: str) -> User:
    if not verify_password(current, user.password_hash):
        raise ValidationFailed("Текущий пароль указан неверно")
    check_new_password(new, user.login)
    if new == current:
        raise ValidationFailed("Новый пароль должен отличаться от текущего")
    user.password_hash = hash_password(new)
    user.must_change_password = False
    audit.record(db, user=user, entity_type="user", entity_id=user.id, action="password_changed")
    db.commit()
    db.refresh(user)
    return user


def _login_free(db: Session, login: str, except_id: uuid.UUID | None = None) -> None:
    other = db.scalar(select(User).where(User.login == login))
    if other is not None and other.id != except_id:
        raise ConflictError("Этот логин уже занят")


def create_account(db: Session, admin: User | None, *, first_name: str, last_name: str | None, login: str,
                   role: UserRole) -> tuple[User, str]:
    login = normalize_login(login)
    _login_free(db, login)
    password = temporary_password()
    user = User(first_name=first_name.strip(), last_name=(last_name or "").strip() or None, login=login,
                password_hash=hash_password(password), must_change_password=True, role=role, is_active=True)
    db.add(user)
    db.flush()
    audit.record(db, user=admin, entity_type="user", entity_id=user.id, action="account_created", comment=None if admin else "Панель владельца",
                 new={"login": login, "role": role.value, "name": user.display_name})
    db.commit()
    db.refresh(user)
    return user, password


def reset_password(db: Session, admin: User | None, user_id: uuid.UUID, login: str | None) -> tuple[User, str]:
    """New temporary password (and a login for a Telegram user who had none). Logs the person out everywhere."""
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("Пользователь не найден")
    if admin is not None and user.id == admin.id:
        raise ConflictError("Свой пароль меняйте в «Ещё → Сменить пароль»")
    changes: dict = {}
    if login is not None and normalize_login(login) != user.login:
        new_login = normalize_login(login)
        _login_free(db, new_login, user.id)
        changes = {"login": new_login}
        user.login = new_login
    if user.login is None:
        raise ValidationFailed("Укажите логин для входа по паролю")
    password = temporary_password()
    user.password_hash = hash_password(password)
    user.must_change_password = True
    user.failed_logins = 0
    user.locked_until = None
    db.execute(update(DeviceSession).where(DeviceSession.user_id == user.id, DeviceSession.revoked_at.is_(None))
               .values(revoked_at=_now()))
    audit.record(db, user=admin, entity_type="user", entity_id=user.id, action="password_reset", new=changes or None,
                 comment=None if admin else "Панель владельца")
    db.commit()
    db.refresh(user)
    return user, password
