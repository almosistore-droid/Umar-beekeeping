import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class QrCode(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The permanent QR of a hive. `code` is the Telegram startapp payload and never changes."""

    __tablename__ = "qr_codes"
    __table_args__ = (CheckConstraint("print_count >= 0", name="print_count_non_negative"),)

    hive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hives.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    print_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_printed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    hive = relationship("Hive", lazy="joined")
