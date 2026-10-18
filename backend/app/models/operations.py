"""Stage 4: honey harvests, other products, swarms, splits, merges, movements, winterings.

Money values are PostgreSQL generated columns: they can never disagree with the
quantity × price they are computed from.
"""
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Computed,
    Date,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import FamilyStrength, FeedUnit, ProductType, WinteringResult


def _fk(table: str, nullable: bool = False, ondelete: str = "RESTRICT", index: bool = False):
    return mapped_column(UUID(as_uuid=True), ForeignKey(f"{table}.id", ondelete=ondelete), nullable=nullable,
                         index=index)


def _author():
    return mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))


class HoneyHarvest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "honey_harvests"
    __table_args__ = (
        CheckConstraint("weight_kg > 0", name="weight_positive"),
        CheckConstraint("price_per_kg IS NULL OR price_per_kg >= 0", name="price_non_negative"),
        CheckConstraint("frames_count >= 0", name="frames_non_negative"),
        CheckConstraint("harvest_number >= 1", name="number_positive"),
        UniqueConstraint("hive_id", "harvest_year", "harvest_number", name="uq_honey_harvests_hive_year_number"),
        Index("ix_honey_harvests_date", "harvest_date"),
    )

    hive_id: Mapped[uuid.UUID] = _fk("hives")
    apiary_id: Mapped[uuid.UUID] = _fk("apiaries")  # where the hive stood at harvest time
    harvest_date: Mapped[date] = mapped_column(Date, nullable=False)
    harvest_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    harvest_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    honey_type: Mapped[str | None] = mapped_column(String(80))
    frames_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    price_per_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    total_value: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), Computed("weight_kg * price_per_kg", persisted=True)
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = _author()

    author = relationship("User", lazy="joined")


class OtherProduct(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "other_products"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("price_per_unit IS NULL OR price_per_unit >= 0", name="price_non_negative"),
        Index("ix_other_products_date", "collected_at"),
    )

    product_type: Mapped[ProductType] = mapped_column(Enum(ProductType, name="product_type"), nullable=False)
    collected_at: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit: Mapped[FeedUnit] = mapped_column(Enum(FeedUnit, name="feed_unit", create_type=False), nullable=False)
    hive_id: Mapped[uuid.UUID | None] = _fk("hives", nullable=True, index=True)
    apiary_id: Mapped[uuid.UUID | None] = _fk("apiaries", nullable=True)
    price_per_unit: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    total_value: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), Computed("quantity * price_per_unit", persisted=True)
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = _author()

    author = relationship("User", lazy="joined")


class Swarm(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "swarms"
    __table_args__ = (
        CheckConstraint("swarm_count >= 1", name="count_positive"),
        CheckConstraint("new_hive_id IS NULL OR captured", name="settled_only_if_captured"),
    )

    hive_id: Mapped[uuid.UUID] = _fk("hives", index=True)
    swarm_date: Mapped[date] = mapped_column(Date, nullable=False)
    swarm_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    captured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    new_hive_id: Mapped[uuid.UUID | None] = _fk("hives", nullable=True)
    new_queen_id: Mapped[uuid.UUID | None] = _fk("queens", nullable=True)
    actions: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = _author()

    author = relationship("User", lazy="joined")


class HiveSplit(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "hive_splits"
    __table_args__ = (CheckConstraint("source_hive_id <> new_hive_id", name="different_hives"),)

    source_hive_id: Mapped[uuid.UUID] = _fk("hives", index=True)
    new_hive_id: Mapped[uuid.UUID] = _fk("hives")
    split_date: Mapped[date] = mapped_column(Date, nullable=False)
    queen_id: Mapped[uuid.UUID | None] = _fk("queens", nullable=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = _author()

    author = relationship("User", lazy="joined")


hive_merge_sources = Table(
    "hive_merge_sources",
    Base.metadata,
    Column("merge_id", UUID(as_uuid=True), ForeignKey("hive_merges.id", ondelete="RESTRICT"), primary_key=True),
    Column("hive_id", UUID(as_uuid=True), ForeignKey("hives.id", ondelete="RESTRICT"), primary_key=True, index=True),
)


class HiveMerge(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "hive_merges"

    target_hive_id: Mapped[uuid.UUID] = _fk("hives", index=True)
    merge_date: Mapped[date] = mapped_column(Date, nullable=False)
    kept_queen_id: Mapped[uuid.UUID | None] = _fk("queens", nullable=True)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = _author()

    author = relationship("User", lazy="joined")
    sources = relationship("Hive", secondary=hive_merge_sources, lazy="selectin")


class HiveMovement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "hive_movements"
    __table_args__ = (
        CheckConstraint("from_apiary_id <> to_apiary_id", name="different_apiaries"),
        Index("ix_hive_movements_hive", "hive_id", "movement_date"),
    )

    hive_id: Mapped[uuid.UUID] = _fk("hives")
    from_apiary_id: Mapped[uuid.UUID] = _fk("apiaries")
    to_apiary_id: Mapped[uuid.UUID] = _fk("apiaries")
    movement_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    performed_by: Mapped[uuid.UUID | None] = _author()

    performer = relationship("User", lazy="joined")
    from_apiary = relationship("Apiary", foreign_keys=[from_apiary_id], lazy="joined")
    to_apiary = relationship("Apiary", foreign_keys=[to_apiary_id], lazy="joined")


class Wintering(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "winterings"
    __table_args__ = (
        UniqueConstraint("hive_id", "season", name="uq_winterings_hive_season"),
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="end_after_start"),
        CheckConstraint("(result IS NULL) = (end_date IS NULL)", name="result_iff_finished"),
        CheckConstraint("food_kg IS NULL OR food_kg >= 0", name="food_non_negative"),
        CheckConstraint("frames_count IS NULL OR frames_count >= 0", name="frames_non_negative"),
    )

    hive_id: Mapped[uuid.UUID] = _fk("hives")
    season: Mapped[str] = mapped_column(String(9), nullable=False)
    pre_winter_strength: Mapped[FamilyStrength | None] = mapped_column(
        Enum(FamilyStrength, name="family_strength", create_type=False)
    )
    food_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    frames_count: Mapped[int | None] = mapped_column(SmallInteger)
    queen_condition: Mapped[str | None] = mapped_column(String(120))
    pre_winter_treatment: Mapped[str | None] = mapped_column(String(255))
    winter_location: Mapped[str | None] = mapped_column(String(255))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    spring_strength: Mapped[FamilyStrength | None] = mapped_column(
        Enum(FamilyStrength, name="family_strength", create_type=False)
    )
    result: Mapped[WinteringResult | None] = mapped_column(Enum(WinteringResult, name="wintering_result"))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = _author()

    author = relationship("User", lazy="joined")
