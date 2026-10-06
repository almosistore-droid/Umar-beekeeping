from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.telegram import TelegramUser
from app.config import Settings
from app.models.user import User, UserRole


def upsert_telegram_user(db: Session, tg: TelegramUser, settings: Settings) -> User:
    """Create the user on first login, otherwise refresh profile fields.

    Roles are never taken from the client: new users get ADMIN only if their
    telegram id is listed in ADMIN_TELEGRAM_IDS, otherwise DEFAULT_USER_ROLE.
    An existing user's role is never changed here.
    """
    user = db.scalar(select(User).where(User.telegram_id == tg.id))
    if user is None:
        role = (
            UserRole.ADMIN
            if tg.id in settings.admin_telegram_ids
            else UserRole(settings.default_user_role)
        )
        user = User(telegram_id=tg.id, role=role, is_active=True)
        db.add(user)

    user.username = tg.username
    user.first_name = tg.first_name
    user.last_name = tg.last_name
    user.language_code = tg.language_code
    db.commit()
    db.refresh(user)
    return user
