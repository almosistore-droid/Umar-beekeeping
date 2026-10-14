from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.telegram import TelegramUser
from app.config import Settings
from app.models.user import User, UserRole
from app.services import admin_service
from app.services import audit_service as audit


def upsert_telegram_user(db: Session, tg: TelegramUser, settings: Settings) -> User:
    """Create the user on first login, otherwise refresh profile fields.

    Roles are never taken from the client: new users get ADMIN only if their
    telegram id is listed in ADMIN_TELEGRAM_IDS, otherwise DEFAULT_USER_ROLE.
    An existing user's role changes here only when their ID is in ADMIN_TELEGRAM_IDS. A pending invitation from the admin
    (by Telegram ID, then by username) sets the role of a new user.
    """
    user = db.scalar(select(User).where(User.telegram_id == tg.id))
    is_new = user is None
    if is_new:
        role = (
            UserRole.ADMIN
            if tg.id in settings.admin_telegram_ids
            else UserRole(settings.default_user_role)
        )
        user = User(telegram_id=tg.id, role=role, is_active=True)
        db.add(user)
    elif tg.id in settings.admin_telegram_ids and user.role != UserRole.ADMIN:
        # The owner listed this ID in the server config after the person had already logged in
        old_role = user.role
        user.role = UserRole.ADMIN
        audit.record(db, user=user, entity_type="user", entity_id=user.id, action="role_from_config",
                     old={"role": old_role.value}, new={"role": UserRole.ADMIN.value})

    user.username = tg.username
    user.first_name = tg.first_name
    user.last_name = tg.last_name
    user.language_code = tg.language_code
    user.last_seen_at = datetime.now(timezone.utc)

    if is_new:
        # A person the admin added in advance gets the chosen role (ADMIN_TELEGRAM_IDS still wins)
        db.flush()
        invite = admin_service.claim_invite(db, user)
        if invite is not None:
            if user.role != UserRole.ADMIN:
                user.role = invite.role
            audit.record(db, user=user, entity_type="user", entity_id=user.id, action="joined_by_invite",
                         new={"role": user.role.value, "invite_id": str(invite.id)})
    db.commit()
    db.refresh(user)
    return user
