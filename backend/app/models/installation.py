"""State of this installation kept in the database (one row): the paid-until date set from the owner panel.

When the row says `subscription_override`, its date wins over SUBSCRIPTION_UNTIL from the .env (which is only the
starting value), so the owner can extend or close a client without touching the server files.
"""
from datetime import date

from sqlalchemy import Boolean, CheckConstraint, Date, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class InstallationState(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "installation_state"
    __table_args__ = (
        CheckConstraint("singleton", name="single_row"),
        Index("uq_installation_state_singleton", "singleton", unique=True),
    )

    singleton: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    subscription_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    subscription_until: Mapped[date | None] = mapped_column(Date)  # None + override = no limit
    updated_from: Mapped[str | None] = mapped_column(String(40))   # «owner panel», «server»
