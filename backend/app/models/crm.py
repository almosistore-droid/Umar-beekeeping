"""Stage 7: CRM — customers, orders, sales with lines and payments, expenses.

Nothing is deleted: customers are archived, sales / expenses / orders are cancelled with a reason.
Line totals are PostgreSQL generated columns (quantity × price).
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Computed, Date, DateTime, Enum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ExpenseCategory, FeedUnit, OrderStatus, PaymentMethod, SaleCategory


def _fk(table: str, nullable: bool = False, ondelete: str = "RESTRICT", index: bool = True):
    return mapped_column(UUID(as_uuid=True), ForeignKey(f"{table}.id", ondelete=ondelete), nullable=nullable, index=index)


def _author():
    return mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))


_unit = Enum(FeedUnit, name="feed_unit", create_type=False)


class Customer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "customers"

    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(40), index=True)
    city: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_by: Mapped[uuid.UUID | None] = _author()


class Expense(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("(cancelled_at IS NULL) = (cancel_reason IS NULL)", name="cancel_reason_iff_cancelled"),
        Index("ix_expenses_date", "expense_date"),
    )

    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    category: Mapped[ExpenseCategory] = mapped_column(Enum(ExpenseCategory, name="expense_category"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    apiary_id: Mapped[uuid.UUID | None] = _fk("apiaries", nullable=True)
    hive_id: Mapped[uuid.UUID | None] = _fk("hives", nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[uuid.UUID | None] = _author()

    apiary = relationship("Apiary", lazy="joined")
    author = relationship("User", lazy="joined")


class _Line:
    """Columns shared by sale and order lines."""
    category: Mapped[SaleCategory] = mapped_column(Enum(SaleCategory, name="sale_category"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit: Mapped[FeedUnit] = mapped_column(_unit, nullable=False)
    price_per_unit: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), Computed("quantity * price_per_unit", persisted=True))
    description: Mapped[str | None] = mapped_column(String(200))


class Order(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("due_date IS NULL OR due_date >= order_date", name="due_after_order"),
        Index("ix_orders_status", "status"),
    )

    customer_id: Mapped[uuid.UUID] = _fk("customers")
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus, name="order_status"), nullable=False,
                                                default=OrderStatus.NEW)
    notes: Mapped[str | None] = mapped_column(Text)
    cancel_reason: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[uuid.UUID | None] = _author()

    customer = relationship("Customer", lazy="joined")
    items = relationship("OrderItem", lazy="selectin", order_by="OrderItem.created_at")
    sale = relationship("Sale", back_populates="order", uselist=False, lazy="selectin")


class OrderItem(_Line, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("price_per_unit >= 0", name="price_non_negative"),
    )
    order_id: Mapped[uuid.UUID] = _fk("orders")


class Sale(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sales"
    __table_args__ = (
        CheckConstraint("(cancelled_at IS NULL) = (cancel_reason IS NULL)", name="cancel_reason_iff_cancelled"),
        Index("ix_sales_date", "sale_date"),
    )

    sale_date: Mapped[date] = mapped_column(Date, nullable=False)
    customer_id: Mapped[uuid.UUID | None] = _fk("customers", nullable=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="RESTRICT"), unique=True)
    notes: Mapped[str | None] = mapped_column(Text)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[uuid.UUID | None] = _author()

    customer = relationship("Customer", lazy="joined")
    author = relationship("User", lazy="joined")
    order = relationship("Order", back_populates="sale", lazy="joined")
    items = relationship("SaleItem", lazy="selectin", order_by="SaleItem.created_at")
    payments = relationship("Payment", lazy="selectin", order_by="Payment.paid_at")


class SaleItem(_Line, UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sale_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("price_per_unit >= 0", name="price_non_negative"),
    )
    sale_id: Mapped[uuid.UUID] = _fk("sales")


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)

    sale_id: Mapped[uuid.UUID] = _fk("sales")
    paid_at: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod, name="payment_method"), nullable=False,
                                                  default=PaymentMethod.CASH)
    notes: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[uuid.UUID | None] = _author()
