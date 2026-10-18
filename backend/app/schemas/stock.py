import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.stock import StockCategory, StockMovementKind, StockUnit
from app.schemas.common import ORMModel, clean_text, not_in_future

Qty = Decimal


class NormsIn(BaseModel):
    wire_m_per_frame: Decimal = Field(ge=0, le=100, decimal_places=3)
    foundation_g_per_frame: Decimal = Field(ge=0, le=5000, decimal_places=2)
    sugar_kg_per_l_syrup: Decimal = Field(ge=0, le=5, decimal_places=3)
    sugar_kg_per_kg_syrup: Decimal = Field(ge=0, le=5, decimal_places=3)


class NormsOut(NormsIn, ORMModel):
    updated_at: datetime | None = None


class StockItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: StockCategory = StockCategory.OTHER
    unit: StockUnit = StockUnit.PCS
    min_quantity: Decimal | None = Field(default=None, ge=0, le=Decimal("1000000"), decimal_places=3)
    notes: str | None = Field(default=None, max_length=2000)
    # first receipt right away (optional)
    initial_quantity: Decimal | None = Field(default=None, gt=0, le=Decimal("1000000"), decimal_places=3)
    initial_amount: Decimal | None = Field(default=None, gt=0, le=Decimal("1000000000"), decimal_places=2)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("Укажите название")
        return v

    @field_validator("notes")
    @classmethod
    def _notes(cls, v):
        return clean_text(v)


class StockItemUpdate(StockItemIn):
    initial_quantity: None = None
    initial_amount: None = None


class StockItemOut(ORMModel):
    id: uuid.UUID
    code: str | None
    name: str
    category: StockCategory
    unit: StockUnit
    min_quantity: Decimal | None
    notes: str | None
    is_archived: bool
    quantity: Decimal = Decimal("0")
    low: bool = False


class MovementIn(BaseModel):
    kind: Literal["RECEIPT", "CONSUMPTION", "INVENTORY"]
    # RECEIPT / CONSUMPTION: how much came in / was used; INVENTORY: how much there really is now
    quantity: Decimal = Field(ge=0, le=Decimal("1000000"), decimal_places=3)
    moved_at: date | None = None
    note: str | None = Field(default=None, max_length=255)
    # receipt only: what was paid — the same sum becomes a CRM expense
    amount: Decimal | None = Field(default=None, gt=0, le=Decimal("1000000000"), decimal_places=2)

    @field_validator("moved_at")
    @classmethod
    def _date(cls, v):
        return not_in_future(v, "Дата")

    @field_validator("note")
    @classmethod
    def _note(cls, v):
        return clean_text(v)


class MovementOut(ORMModel):
    id: uuid.UUID
    item_id: uuid.UUID
    moved_at: date
    kind: StockMovementKind
    quantity: Decimal
    note: str | None
    frame_prep_id: uuid.UUID | None
    feeding_id: uuid.UUID | None
    treatment_id: uuid.UUID | None
    hive_id: uuid.UUID | None = None
    hive_number: str | None = None
    amount: Decimal | None = None   # shown to ADMIN / BEEKEEPER only
    expense_id: uuid.UUID | None = None
    cancelled_at: datetime | None
    author_name: str | None = None
    created_at: datetime


class StockItemDetails(BaseModel):
    item: StockItemOut
    movements: list[MovementOut]


class StockOverview(BaseModel):
    items: list[StockItemOut]
    honey_kg: Decimal
    norms: NormsOut


class FramePrepIn(BaseModel):
    frames: int = Field(gt=0, le=10000)
    prepared_at: date | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("prepared_at")
    @classmethod
    def _date(cls, v):
        return not_in_future(v, "Дата")

    @field_validator("notes")
    @classmethod
    def _notes(cls, v):
        return clean_text(v)


class UseLine(BaseModel):
    """One line of an automatic write-off: what, how much and what remains."""
    item_id: uuid.UUID
    name: str
    unit: StockUnit
    quantity: Decimal          # signed, as the movement
    balance_after: Decimal


class FramePrepOut(ORMModel):
    id: uuid.UUID
    prepared_at: date
    frames: int
    wire_m_per_frame: Decimal
    foundation_g_per_frame: Decimal
    notes: str | None
    cancelled_at: datetime | None
    created_at: datetime


class FramePrepResult(BaseModel):
    prep: FramePrepOut
    lines: list[UseLine]


class CancelIn(BaseModel):
    reason: str = Field(min_length=1, max_length=255)
