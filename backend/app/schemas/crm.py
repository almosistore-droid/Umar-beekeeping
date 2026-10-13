"""Stage 7 CRM schemas. Messages are Russian; money is Decimal with 2 places."""
import re
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import ExpenseCategory, FeedUnit, OrderStatus, PaymentMethod, SaleCategory
from app.schemas.common import clean_text, not_in_future

Money = Field(gt=0, le=Decimal("10000000000"), decimal_places=2)
_PHONE_RE = re.compile(r"^\+?\d{6,15}$")


def _phone(v: str | None) -> str | None:
    v = clean_text(v)
    if v is None:
        return None
    compact = re.sub(r"[\s\-()]", "", v)
    if not _PHONE_RE.match(compact):
        raise ValueError("Телефон: от 6 до 15 цифр, можно с «+» в начале")
    return compact


# ---------- customers ----------

class CustomerIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    city: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("name")
    @classmethod
    def _name(cls, v):
        v = clean_text(v) or ""
        if len(v) < 2:
            raise ValueError("Имя клиента: не короче 2 символов")
        return v

    @field_validator("phone")
    @classmethod
    def _ph(cls, v):
        return _phone(v)

    @field_validator("city", "notes")
    @classmethod
    def _txt(cls, v):
        return clean_text(v)


class CustomerUpdate(CustomerIn):
    name: str | None = Field(default=None, min_length=2, max_length=120)  # type: ignore[assignment]
    is_archived: bool | None = None


class CustomerBrief(BaseModel):
    id: uuid.UUID
    name: str
    phone: str | None


class CustomerOut(CustomerBrief):
    city: str | None
    notes: str | None
    is_archived: bool
    created_at: datetime
    bought: Decimal
    paid: Decimal
    debt: Decimal
    sales_count: int
    last_purchase: date | None


# ---------- lines ----------

class LineIn(BaseModel):
    category: SaleCategory
    quantity: Decimal = Field(gt=0, le=Decimal("1000000"), decimal_places=2)
    unit: FeedUnit = FeedUnit.KG
    price_per_unit: Decimal = Field(ge=0, le=Decimal("1000000000"), decimal_places=2)
    description: str | None = Field(default=None, max_length=200)

    @field_validator("description")
    @classmethod
    def _d(cls, v):
        return clean_text(v)


class LineOut(BaseModel):
    id: uuid.UUID
    category: SaleCategory
    quantity: Decimal
    unit: FeedUnit
    price_per_unit: Decimal
    total: Decimal
    description: str | None


# ---------- payments ----------

class PaymentIn(BaseModel):
    amount: Decimal = Money
    paid_at: date | None = None
    method: PaymentMethod = PaymentMethod.CASH
    notes: str | None = Field(default=None, max_length=255)

    @field_validator("paid_at")
    @classmethod
    def _when(cls, v):
        return not_in_future(v, "Дата оплаты")


class PaymentOut(BaseModel):
    id: uuid.UUID
    sale_id: uuid.UUID
    paid_at: date
    amount: Decimal
    method: PaymentMethod
    notes: str | None


class PayNow(BaseModel):
    """Payment at the moment of a sale or delivery of an order."""
    payment: Literal["full", "partial", "credit"] = "full"
    paid_amount: Decimal | None = Field(default=None, gt=0, le=Decimal("10000000000"), decimal_places=2)
    method: PaymentMethod = PaymentMethod.CASH

    @model_validator(mode="after")
    def _partial(self):
        if self.payment == "partial" and self.paid_amount is None:
            raise ValueError("Укажите, сколько заплатили сейчас")
        return self


# ---------- sales ----------

class SaleCreate(PayNow):
    sale_date: date | None = None
    customer_id: uuid.UUID | None = None
    items: list[LineIn] = Field(min_length=1, max_length=30)
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("sale_date")
    @classmethod
    def _when(cls, v):
        return not_in_future(v, "Дата продажи")


class SaleUpdate(BaseModel):
    sale_date: date | None = None
    customer_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=5000)
    comment: str | None = Field(default=None, max_length=1000)

    @field_validator("sale_date")
    @classmethod
    def _when(cls, v):
        return not_in_future(v, "Дата продажи")


SaleState = Literal["paid", "partial", "unpaid", "cancelled"]


class SaleOut(BaseModel):
    id: uuid.UUID
    sale_date: date
    customer: CustomerBrief | None
    order_id: uuid.UUID | None
    notes: str | None
    items: list[LineOut]
    payments: list[PaymentOut]
    total: Decimal
    paid: Decimal
    debt: Decimal
    state: SaleState
    cancelled_at: datetime | None
    cancel_reason: str | None
    author: str | None
    created_at: datetime


class CancelIn(BaseModel):
    reason: str = Field(min_length=3, max_length=255)

    @field_validator("reason")
    @classmethod
    def _r(cls, v):
        v = clean_text(v) or ""
        if len(v) < 3:
            raise ValueError("Укажите причину отмены")
        return v


# ---------- expenses ----------

class ExpenseIn(BaseModel):
    expense_date: date | None = None
    category: ExpenseCategory
    amount: Decimal = Money
    description: str | None = Field(default=None, max_length=5000)
    apiary_id: uuid.UUID | None = None
    hive_id: uuid.UUID | None = None

    @field_validator("expense_date")
    @classmethod
    def _when(cls, v):
        return not_in_future(v, "Дата расхода")

    @field_validator("description")
    @classmethod
    def _d(cls, v):
        return clean_text(v)


class ExpenseUpdate(BaseModel):
    expense_date: date | None = None
    category: ExpenseCategory | None = None
    amount: Decimal | None = Field(default=None, gt=0, le=Decimal("10000000000"), decimal_places=2)
    description: str | None = Field(default=None, max_length=5000)
    apiary_id: uuid.UUID | None = None
    comment: str | None = Field(default=None, max_length=1000)

    @field_validator("expense_date")
    @classmethod
    def _when(cls, v):
        return not_in_future(v, "Дата расхода")


class ExpenseOut(BaseModel):
    id: uuid.UUID
    expense_date: date
    category: ExpenseCategory
    amount: Decimal
    description: str | None
    apiary_id: uuid.UUID | None
    apiary_name: str | None
    hive_id: uuid.UUID | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    author: str | None
    created_at: datetime


# ---------- orders ----------

class OrderCreate(BaseModel):
    customer_id: uuid.UUID
    order_date: date | None = None
    due_date: date | None = None
    items: list[LineIn] = Field(min_length=1, max_length=30)
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("order_date")
    @classmethod
    def _when(cls, v):
        return not_in_future(v, "Дата заказа")


class OrderUpdate(BaseModel):
    due_date: date | None = None
    notes: str | None = Field(default=None, max_length=5000)
    items: list[LineIn] | None = Field(default=None, min_length=1, max_length=30)
    status: Literal["READY"] | None = None  # DELIVERED → /deliver, CANCELLED → /cancel


class DeliverIn(PayNow):
    sale_date: date | None = None

    @field_validator("sale_date")
    @classmethod
    def _when(cls, v):
        return not_in_future(v, "Дата выдачи")


class OrderOut(BaseModel):
    id: uuid.UUID
    customer: CustomerBrief
    order_date: date
    due_date: date | None
    status: OrderStatus
    notes: str | None
    cancel_reason: str | None
    items: list[LineOut]
    total: Decimal
    overdue: bool
    sale_id: uuid.UUID | None
    sale_state: SaleState | None
    sale_debt: Decimal | None
    created_at: datetime


class CustomerDetails(CustomerOut):
    orders: list[OrderOut]
    sales: list[SaleOut]


# ---------- debts & summary ----------

class DebtorOut(BaseModel):
    customer: CustomerBrief | None  # None: sales without a customer
    debt: Decimal
    sales: list[SaleOut]


class AmountByKey(BaseModel):
    key: str
    label: str
    amount: Decimal


class CrmSummary(BaseModel):
    year: int
    month: int | None
    currency: str
    income: Decimal
    expenses: Decimal
    profit: Decimal
    received: Decimal
    debts_total: Decimal
    debtors: int
    open_orders: int
    honey_stock_kg: Decimal
    income_by_month: list[Decimal]
    expenses_by_month: list[Decimal]
    income_by_category: list[AmountByKey]
    expenses_by_category: list[AmountByKey]
