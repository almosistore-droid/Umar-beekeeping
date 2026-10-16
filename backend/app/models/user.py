import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    BEEKEEPER = "BEEKEEPER"
    ASSISTANT = "ASSISTANT"
    VIEWER = "VIEWER"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("language IS NULL OR language IN ('ru', 'tg')", name="language_known"),
        CheckConstraint("telegram_id IS NOT NULL OR login IS NOT NULL", name="telegram_or_login"),
        CheckConstraint("login IS NULL OR login = lower(login)", name="login_lowercase"),
    )

    # Telegram account (Mini App, login through the bot); null for people who log in only with a password
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(128))
    last_name: Mapped[str | None] = mapped_column(String(128))
    language_code: Mapped[str | None] = mapped_column(String(16))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False, default=UserRole.VIEWER
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Language chosen in the app (ru / tg); null = follow Telegram's language
    language: Mapped[str | None] = mapped_column(String(2))
    # Last successful login through Telegram (shown in the admin panel)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Login with a password (no Telegram needed). The admin creates it with a temporary password.
    login: Mapped[str | None] = mapped_column(String(32), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    failed_logins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def display_name(self) -> str:
        full = " ".join(p for p in (self.first_name, self.last_name) if p)
        return full or (f"@{self.username}" if self.username else self.login or str(self.telegram_id))

    @property
    def has_password(self) -> bool:
        return self.password_hash is not None


class InviteStatus(str, enum.Enum):
    PENDING = "PENDING"
    USED = "USED"
    REVOKED = "REVOKED"


class UserInvite(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A person added in advance by the admin: gets `role` on the first login (by Telegram ID or username)."""

    __tablename__ = "user_invites"
    __table_args__ = (
        CheckConstraint("telegram_id IS NOT NULL OR username IS NOT NULL", name="id_or_username"),
        CheckConstraint("username IS NULL OR username = lower(username)", name="username_lowercase"),
        Index("uq_user_invites_pending_telegram_id", "telegram_id", unique=True,
              postgresql_where=text("status = 'PENDING' AND telegram_id IS NOT NULL")),
        Index("uq_user_invites_pending_username", "username", unique=True,
              postgresql_where=text("status = 'PENDING' AND username IS NOT NULL")),
    )

    telegram_id: Mapped[int | None] = mapped_column(BigInteger)
    username: Mapped[str | None] = mapped_column(String(64))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role", create_type=False), nullable=False)
    note: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[InviteStatus] = mapped_column(Enum(InviteStatus, name="invite_status"), nullable=False,
                                                 default=InviteStatus.PENDING)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    used_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    author = relationship("User", foreign_keys=[created_by], lazy="joined")
    joined = relationship("User", foreign_keys=[used_by], lazy="joined")
