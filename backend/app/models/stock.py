"""Warehouse: frames, foundation, wire, feed, medicines and the owner's own items.

The balance of an item is never stored: it is the sum of its movements that are not cancelled.
Movements are never deleted — a mistake is cancelled (with the reason in the audit log) or corrected
by an inventory count. Frame preparation, feedings and treatments write their movements automatically
using the consumption norms (`stock_norms`, one row).
"""
import enum
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
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class StockCategory(str, enum.Enum):
    FRAMES = "FRAMES"      # frames, foundation, wire
    FEED = "FEED"
    MEDICINE = "MEDICINE"
    OTHER = "OTHER"


class StockUnit(str, enum.Enum):
    PCS = "PCS"
    KG = "KG"
    G = "G"
    L = "L"
    ML = "ML"
    M = "M"
    PACK = "PACK"


class StockMovementKind(str, enum.Enum):
    RECEIPT = "RECEIPT"          # bought / received (+)
    CONSUMPTION = "CONSUMPTION"  # used by hand (−)
    INVENTORY = "INVENTORY"      # count correction (±)
    FRAME_PREP = "FRAME_PREP"    # frames prepared: wire, foundation, empty frames −, ready frames +
    FEEDING = "FEEDING"          # feeding record (−)
    TREATMENT = "TREATMENT"      # treatment record (−)


MANUAL_KINDS = frozenset({StockMovementKind.RECEIPT, StockMovementKind.CONSUMPTION, StockMovementKind.INVENTORY})

# Items the system needs for its calculations; created by migration 0012, cannot be archived
FRAMES_EMPTY, FRAMES_READY, FOUNDATION, WIRE = "frames_empty", "frames_ready", "foundation", "wire"
SUGAR, CANDY, PROTEIN = "sugar", "candy", "protein"


def _author():
    return mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))


class StockItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "stock_items"
    __table_args__ = (
        CheckConstraint("min_quantity IS NULL OR min_quantity >= 0", name="min_not_negative"),
        CheckConstraint("code IS NULL OR NOT is_archived", name="system_not_archived"),
        Index("uq_stock_items_code", "code", unique=True, postgresql_where=text("code IS NOT NULL")),
        Index("uq_stock_items_active_name", text("lower(name)"), unique=True,
              postgresql_where=text("NOT is_archived")),
    )

    code: Mapped[str | None] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[StockCategory] = mapped_column(Enum(StockCategory, name="stock_category"), nullable=False)
    unit: Mapped[StockUnit] = mapped_column(Enum(StockUnit, name="stock_unit"), nullable=False)
    min_quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    notes: Mapped[str | None] = mapped_column(Text)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_by: Mapped[uuid.UUID | None] = _author()


class FramePreparation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """«Prepared N frames»: the norms used are kept, so later norm changes do not rewrite history."""
    __tablename__ = "frame_preparations"
    __table_args__ = (
        CheckConstraint("frames > 0", name="frames_positive"),
        CheckConstraint("wire_m_per_frame >= 0 AND foundation_g_per_frame >= 0", name="norms_not_negative"),
    )

    prepared_at: Mapped[date] = mapped_column(Date, nullable=False)
    frames: Mapped[int] = mapped_column(Integer, nullable=False)
    wire_m_per_frame: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    foundation_g_per_frame: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = _author()

    author = relationship("User", lazy="joined")


class StockMovement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint("quantity <> 0", name="quantity_not_zero"),
        Index("ix_stock_movements_item_date", "item_id", "moved_at"),
        Index("ix_stock_movements_feeding", "feeding_id", postgresql_where=text("feeding_id IS NOT NULL")),
        Index("ix_stock_movements_treatment", "treatment_id", postgresql_where=text("treatment_id IS NOT NULL")),
        Index("ix_stock_movements_frame_prep", "frame_prep_id", postgresql_where=text("frame_prep_id IS NOT NULL")),
    )

    item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("stock_items.id", ondelete="RESTRICT"),
                                               nullable=False)
    moved_at: Mapped[date] = mapped_column(Date, nullable=False)
    kind: Mapped[StockMovementKind] = mapped_column(Enum(StockMovementKind, name="stock_movement_kind"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)  # + in, − out
    note: Mapped[str | None] = mapped_column(String(255))
    frame_prep_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("frame_preparations.id", ondelete="RESTRICT"))
    feeding_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("feedings.id", ondelete="RESTRICT"))
    treatment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("treatments.id", ondelete="RESTRICT"))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = _author()

    item = relationship("StockItem", lazy="joined")
    author = relationship("User", lazy="joined")


class StockNorms(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Consumption norms (one row, created by migration 0012), edited in «Ещё → Нормы расхода»."""
    __tablename__ = "stock_norms"
    __table_args__ = (
        CheckConstraint("singleton", name="single_row"),
        Index("uq_stock_norms_singleton", "singleton", unique=True),
        CheckConstraint("wire_m_per_frame >= 0 AND foundation_g_per_frame >= 0 AND sugar_kg_per_l_syrup >= 0 "
                        "AND sugar_kg_per_kg_syrup >= 0", name="norms_not_negative"),
    )

    singleton: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    wire_m_per_frame: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False, default=Decimal("3"))
    foundation_g_per_frame: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=Decimal("110"))
    # syrup 1:1 — 1 kg sugar + 1 l water ≈ 1.6 l of syrup
    sugar_kg_per_l_syrup: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False, default=Decimal("0.63"))
    sugar_kg_per_kg_syrup: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False, default=Decimal("0.5"))
    updated_by: Mapped[uuid.UUID | None] = _author()
