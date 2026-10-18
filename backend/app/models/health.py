"""Stage 3: inspections, disease catalog and cases, treatments, feedings, reminder tasks.

Nothing here is ever deleted: cases end as RESOLVED, tasks as DONE/CANCELLED, and
corrections are recorded in audit_logs.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    DiseaseCaseStatus,
    DiseaseSeverity,
    FamilyStrength,
    FeedType,
    FeedUnit,
    FoodLevel,
    InspectionHealth,
    QueenCondition,
    TaskKind,
    TaskStatus,
)


def _hive_fk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), ForeignKey("hives.id", ondelete="RESTRICT"), nullable=False)


def _user_fk(nullable: bool = True):
    return mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=nullable)


class ClientUidMixin:
    """Id made by the phone for records saved without internet: sending it twice creates one record."""
    client_uid: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), unique=True)


class Inspection(ClientUidMixin, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "hive_inspections"
    __table_args__ = (
        CheckConstraint("frames_total BETWEEN 0 AND 60", name="frames_total_range"),
        CheckConstraint("brood_frames >= 0 AND honey_frames >= 0 AND pollen_frames >= 0", name="frames_non_negative"),
        CheckConstraint("brood_frames + honey_frames + pollen_frames <= frames_total", name="frames_sum"),
        CheckConstraint("queen_cells >= 0", name="queen_cells_non_negative"),
        CheckConstraint("aggressiveness IS NULL OR aggressiveness BETWEEN 1 AND 5", name="aggressiveness_1_5"),
        Index("ix_hive_inspections_hive_time", "hive_id", "inspected_at"),
    )

    hive_id: Mapped[uuid.UUID] = _hive_fk()
    user_id: Mapped[uuid.UUID | None] = _user_fk()
    inspected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    strength: Mapped[FamilyStrength] = mapped_column(
        Enum(FamilyStrength, name="family_strength", create_type=False), nullable=False
    )
    frames_total: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    brood_frames: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    honey_frames: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    pollen_frames: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    queen_present: Mapped[bool | None] = mapped_column(Boolean)
    queen_condition: Mapped[QueenCondition | None] = mapped_column(Enum(QueenCondition, name="queen_condition"))
    egg_laying: Mapped[bool | None] = mapped_column(Boolean)
    queen_cells: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    swarming_signs: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    food_level: Mapped[FoodLevel | None] = mapped_column(Enum(FoodLevel, name="food_level"))
    aggressiveness: Mapped[int | None] = mapped_column(SmallInteger)
    health_status: Mapped[InspectionHealth] = mapped_column(
        Enum(InspectionHealth, name="inspection_health"), nullable=False, default=InspectionHealth.HEALTHY
    )
    next_inspection_at: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)

    user = relationship("User", lazy="joined")


class Disease(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "diseases"

    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_quarantine: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=100)


class HiveDisease(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One disease case in one hive."""

    __tablename__ = "hive_diseases"
    __table_args__ = (
        CheckConstraint("resolved_at IS NULL OR resolved_at >= detected_at", name="resolved_after_detected"),
        CheckConstraint("(status = 'RESOLVED') = (resolved_at IS NOT NULL)", name="resolved_date_iff_resolved"),
        Index("ix_hive_diseases_hive_status", "hive_id", "status"),
    )

    hive_id: Mapped[uuid.UUID] = _hive_fk()
    disease_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("diseases.id", ondelete="RESTRICT"), nullable=False
    )
    detected_at: Mapped[date] = mapped_column(Date, nullable=False)
    severity: Mapped[DiseaseSeverity] = mapped_column(
        Enum(DiseaseSeverity, name="disease_severity"), nullable=False, default=DiseaseSeverity.MODERATE
    )
    symptoms: Mapped[str | None] = mapped_column(Text)
    diagnosis: Mapped[str | None] = mapped_column(Text)
    status: Mapped[DiseaseCaseStatus] = mapped_column(
        Enum(DiseaseCaseStatus, name="disease_case_status"), nullable=False, default=DiseaseCaseStatus.SUSPECTED
    )
    resolved_at: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = _user_fk()

    disease = relationship("Disease", lazy="joined")
    author = relationship("User", lazy="joined")


class Treatment(ClientUidMixin, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "treatments"
    __table_args__ = (
        CheckConstraint("next_treatment_date IS NULL OR next_treatment_date >= treated_at", name="next_after_date"),
        Index("ix_treatments_hive_date", "hive_id", "treated_at"),
    )

    hive_id: Mapped[uuid.UUID] = _hive_fk()
    disease_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("diseases.id", ondelete="RESTRICT")
    )
    hive_disease_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hive_diseases.id", ondelete="RESTRICT")
    )
    treated_at: Mapped[date] = mapped_column(Date, nullable=False)
    medication: Mapped[str] = mapped_column(String(120), nullable=False)
    dosage: Mapped[str | None] = mapped_column(String(120))
    method: Mapped[str | None] = mapped_column(String(120))
    performed_by: Mapped[uuid.UUID | None] = _user_fk()
    result: Mapped[str | None] = mapped_column(Text)
    next_treatment_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)

    disease = relationship("Disease", lazy="joined")
    performer = relationship("User", lazy="joined")


class Feeding(ClientUidMixin, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "feedings"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("next_feeding_date IS NULL OR next_feeding_date >= fed_at", name="next_after_date"),
        Index("ix_feedings_hive_date", "hive_id", "fed_at"),
    )

    hive_id: Mapped[uuid.UUID] = _hive_fk()
    fed_at: Mapped[date] = mapped_column(Date, nullable=False)
    feed_type: Mapped[FeedType] = mapped_column(Enum(FeedType, name="feed_type"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit: Mapped[FeedUnit] = mapped_column(Enum(FeedUnit, name="feed_unit"), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255))
    result: Mapped[str | None] = mapped_column(Text)
    next_feeding_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = _user_fk()

    author = relationship("User", lazy="joined")


class Task(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A reminder: something to do for a hive by a date. Sent by the bot in stage 8."""

    __tablename__ = "tasks"
    __table_args__ = (Index("ix_tasks_status_due", "status", "due_date"),)

    hive_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hives.id", ondelete="RESTRICT"), index=True
    )
    kind: Mapped[TaskKind] = mapped_column(Enum(TaskKind, name="task_kind"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus, name="task_status"), nullable=False, default=TaskStatus.OPEN)
    source_type: Mapped[str | None] = mapped_column(String(40))
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)  # record / rearing batch
    created_by: Mapped[uuid.UUID | None] = _user_fk()
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_by: Mapped[uuid.UUID | None] = _user_fk()
