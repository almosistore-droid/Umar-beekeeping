"""Login on a phone outside Telegram (the app installed on the home screen).

LoginCode: a one-time code the user confirms in the bot (`t.me/<bot>?start=login_<code>`).
DeviceSession: a logged-in phone; its random token is stored only as a SHA-256 hash.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LoginCodeStatus(str, enum.Enum):
    PENDING = "PENDING"      # waiting for «Войти» in the bot
    CONFIRMED = "CONFIRMED"  # confirmed in the bot, the device has not collected the session yet
    DENIED = "DENIED"        # «Отмена» in the bot
    USED = "USED"            # the device received its session


class LoginCode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "login_codes"

    code_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    # Secret known only to the device that asked for the code: nobody else can collect the session
    poll_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[LoginCodeStatus] = mapped_column(Enum(LoginCodeStatus, name="login_code_status"), nullable=False,
                                                    default=LoginCodeStatus.PENDING)
    device_name: Mapped[str | None] = mapped_column(String(120))
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DeviceSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "device_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(120))
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user = relationship("User", lazy="joined")
