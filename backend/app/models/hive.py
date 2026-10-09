import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    FamilyOrigin,
    FamilyStatus,
    FamilyStrength,
    HiveStatus,
    HiveType,
    QueenOrigin,
    QueenStatus,
)


class Hive(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A physical hive. Its UUID never changes: it is what the QR code points to."""

    __tablename__ = "hives"
    __table_args__ = (
        # A number is unique within an apiary among hives that are not archived
        Index(
            "uq_hives_apiary_number_active",
            "apiary_id",
            "hive_number",
            unique=True,
            postgresql_where=text("status NOT IN ('MERGED', 'SOLD', 'LOST')"),
        ),
        CheckConstraint("version >= 1", name="version_positive"),
    )

    apiary_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("apiaries.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    hive_number: Mapped[str] = mapped_column(String(20), nullable=False)
    hive_type: Mapped[HiveType] = mapped_column(Enum(HiveType, name="hive_type"), nullable=False)
    status: Mapped[HiveStatus] = mapped_column(
        Enum(HiveStatus, name="hive_status"), nullable=False, default=HiveStatus.EMPTY, index=True
    )
    installation_date: Mapped[date | None] = mapped_column(Date)
    colonization_date: Mapped[date | None] = mapped_column(Date)
    current_family_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bee_families.id", ondelete="SET NULL", use_alter=True),
    )
    current_queen_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("queens.id", ondelete="SET NULL", use_alter=True),
    )
    last_inspection_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_inspection_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    # Incremented on every change; clients send it back to detect conflicting edits
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    apiary = relationship("Apiary", back_populates="hives", lazy="joined")
    current_family = relationship("BeeFamily", foreign_keys=[current_family_id], lazy="joined")
    current_queen = relationship("Queen", foreign_keys=[current_queen_id], lazy="joined")


class BeeFamily(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A bee colony living in a hive for a period. Old families stay as history."""

    __tablename__ = "bee_families"
    __table_args__ = (
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="dates_order"),
        # At most one active family per hive
        Index(
            "uq_bee_families_active_per_hive",
            "hive_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    hive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hives.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    strength: Mapped[FamilyStrength] = mapped_column(
        Enum(FamilyStrength, name="family_strength"), nullable=False, default=FamilyStrength.MEDIUM
    )
    status: Mapped[FamilyStatus] = mapped_column(
        Enum(FamilyStatus, name="family_status"), nullable=False, default=FamilyStatus.ACTIVE
    )
    origin: Mapped[FamilyOrigin] = mapped_column(
        Enum(FamilyOrigin, name="family_origin"), nullable=False, default=FamilyOrigin.OTHER
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    end_reason: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)


class Queen(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A queen bee. Age is never stored: it is computed from birth_date / birth_year."""

    __tablename__ = "queens"
    __table_args__ = (
        CheckConstraint("birth_year IS NULL OR birth_year BETWEEN 1990 AND 2200", name="birth_year_range"),
        CheckConstraint(
            "birth_date IS NULL OR birth_year IS NULL OR EXTRACT(YEAR FROM birth_date) = birth_year",
            name="birth_year_matches_date",
        ),
        CheckConstraint("egg_laying_quality IS NULL OR egg_laying_quality BETWEEN 1 AND 5", name="egg_laying_1_5"),
        CheckConstraint("swarming_tendency IS NULL OR swarming_tendency BETWEEN 1 AND 5", name="swarming_1_5"),
        CheckConstraint("temperament IS NULL OR temperament BETWEEN 1 AND 5", name="temperament_1_5"),
        CheckConstraint("removed_at IS NULL OR installed_at IS NULL OR removed_at >= installed_at", name="removal_after_install"),
        # One main queen per hive
        Index(
            "uq_queens_current_hive",
            "current_hive_id",
            unique=True,
            postgresql_where=text("current_hive_id IS NOT NULL"),
        ),
    )

    queen_code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    birth_date: Mapped[date | None] = mapped_column(Date)
    birth_year: Mapped[int | None] = mapped_column(SmallInteger)
    breed: Mapped[str | None] = mapped_column(String(80))
    origin: Mapped[QueenOrigin] = mapped_column(
        Enum(QueenOrigin, name="queen_origin"), nullable=False, default=QueenOrigin.UNKNOWN
    )
    status: Mapped[QueenStatus] = mapped_column(
        Enum(QueenStatus, name="queen_status"), nullable=False, default=QueenStatus.ACTIVE, index=True
    )
    current_hive_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hives.id", ondelete="SET NULL")
    )
    installed_at: Mapped[date | None] = mapped_column(Date)
    removed_at: Mapped[date | None] = mapped_column(Date)
    removal_reason: Mapped[str | None] = mapped_column(String(255))
    egg_laying_quality: Mapped[int | None] = mapped_column(SmallInteger)
    swarming_tendency: Mapped[int | None] = mapped_column(SmallInteger)
    temperament: Mapped[int | None] = mapped_column(SmallInteger)
    marking_color: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)

    current_hive = relationship("Hive", foreign_keys=[current_hive_id], lazy="noload")


class QueenAssignment(UUIDPrimaryKeyMixin, Base):
    """Every period a queen spent in a hive. This is the queen-replacement history."""

    __tablename__ = "queen_assignments"
    __table_args__ = (
        CheckConstraint("removed_at IS NULL OR removed_at >= installed_at", name="dates_order"),
        Index(
            "uq_queen_assignments_open_per_queen",
            "queen_id",
            unique=True,
            postgresql_where=text("removed_at IS NULL"),
        ),
    )

    queen_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("queens.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    hive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hives.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    installed_at: Mapped[date] = mapped_column(Date, nullable=False)
    removed_at: Mapped[date | None] = mapped_column(Date)
    removal_reason: Mapped[str | None] = mapped_column(String(255))
    installed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    queen = relationship("Queen", lazy="joined")
