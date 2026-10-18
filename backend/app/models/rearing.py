"""Queen rearing: a batch of grafted larvae and its calendar.

Day 0 is the grafting of 12–24 h old larvae. The steps (acceptance, sealing, moving ripe cells, emergence,
mating, laying) are computed from that day in `rearing_service.STEPS` and become reminders (`tasks`,
source_type «rearing:<step>»), so the bot sends them like any other reminder.
"""
import enum
import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RearingStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class RearingBatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rearing_batches"
    __table_args__ = (
        CheckConstraint("cells_grafted > 0", name="grafted_positive"),
        CheckConstraint("cells_accepted IS NULL OR cells_accepted BETWEEN 0 AND cells_grafted", name="accepted_range"),
        CheckConstraint("cells_sealed IS NULL OR cells_sealed BETWEEN 0 AND cells_grafted", name="sealed_range"),
        CheckConstraint("queens_emerged IS NULL OR queens_emerged BETWEEN 0 AND cells_grafted", name="emerged_range"),
        CheckConstraint("queens_mated IS NULL OR queens_mated BETWEEN 0 AND cells_grafted", name="mated_range"),
        CheckConstraint("(status = 'ACTIVE') = (finished_at IS NULL)", name="finished_iff_closed"),
        Index("ix_rearing_batches_status_date", "status", "grafted_at"),
    )

    label: Mapped[str] = mapped_column(String(80), nullable=False)
    grafted_at: Mapped[date] = mapped_column(Date, nullable=False)
    mother_queen_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("queens.id", ondelete="RESTRICT"), index=True)
    cell_builder_hive_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hives.id", ondelete="RESTRICT"), index=True)
    cells_grafted: Mapped[int] = mapped_column(Integer, nullable=False)
    cells_accepted: Mapped[int | None] = mapped_column(Integer)
    cells_sealed: Mapped[int | None] = mapped_column(Integer)
    queens_emerged: Mapped[int | None] = mapped_column(Integer)
    queens_mated: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[RearingStatus] = mapped_column(Enum(RearingStatus, name="rearing_status"), nullable=False,
                                                  default=RearingStatus.ACTIVE)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))

    mother_queen = relationship("Queen", lazy="joined")
    cell_builder = relationship("Hive", lazy="joined")
