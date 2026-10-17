"""Telegram reminders already handled: one row per (person, reminder key), so nothing is sent twice."""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class NotificationLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "notification_log"
    __table_args__ = (
        UniqueConstraint("user_id", "key", name="uq_notification_log_user_key"),
        CheckConstraint("status IN ('SENT', 'FAILED')", name="status_known"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    # e.g. "task:<uuid>:due", "inspection:<hive>:2026-10-17", "debt:<customer>:2026-W42"
    key: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    error: Mapped[str | None] = mapped_column(String(300))
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
