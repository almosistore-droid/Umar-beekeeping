import re
import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import FamilyStrength, FeedUnit, ProductType, WinteringResult
from app.schemas.common import ORMModel, clean_text, not_in_future
from app.schemas.hive import _hive_number

Money = Field(default=None, ge=0, le=Decimal("100000000"), decimal_places=2)
Text = Field(default=None, max_length=5000)


class _Clean(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def _strip(cls, v):
        return clean_text(v) if isinstance(v, str) else v


# ---------- honey ----------

class HarvestFields(_Clean):
    harvest_date: date | None = None
    honey_type: str | None = Field(default=None, max_length=80)
    frames_count: int = Field(default=0, ge=0, le=500)
    weight_kg: Decimal = Field(gt=0, le=Decimal("100000"), decimal_places=2)
    price_per_kg: Decimal | None = Money
    notes: str | None = Text

    @field_validator("harvest_date")
    @classmethod
    def _date(cls, v):
        return not_in_future(v, "Дата откачки")


class HarvestCreate(HarvestFields):
    pass


class HarvestUpdate(HarvestFields):
    comment: str | None = Field(default=None, max_length=1000)


class HarvestOut(ORMModel):
    id: uuid.UUID
    hive_id: uuid.UUID
    apiary_id: uuid.UUID
    harvest_date: date
    harvest_year: int
    harvest_number: int
    honey_type: str | None
    frames_count: int
    weight_kg: Decimal
    price_per_kg: Decimal | None
    total_value: Decimal | None
    notes: str | None
    created_at: datetime


class HiveHoneyOut(BaseModel):
    items: list[HarvestOut]
    year: int
    year_kg: Decimal
    year_value: Decimal
    all_time_kg: Decimal


class HiveRank(BaseModel):
    hive_id: uuid.UUID
    hive_number: str
    apiary_name: str
    kg: Decimal
    harvests: int


class HoneyStats(BaseModel):
    year: int
    month_kg: Decimal
    year_kg: Decimal
    season_kg: Decimal
    all_time_kg: Decimal
    year_value: Decimal
    producing_hives: int
    avg_per_hive_kg: Decimal
    best_hive: HiveRank | None
    by_month: list[Decimal]
    by_hive: list[HiveRank]


# ---------- products ----------

class ProductCreate(_Clean):
    product_type: ProductType
    collected_at: date | None = None
    quantity: Decimal = Field(gt=0, le=Decimal("1000000"), decimal_places=2)
    unit: FeedUnit
    hive_id: uuid.UUID | None = None
    apiary_id: uuid.UUID | None = None
    price_per_unit: Decimal | None = Money
    notes: str | None = Text

    @field_validator("collected_at")
    @classmethod
    def _date(cls, v):
        return not_in_future(v, "Дата")


class ProductOut(ORMModel):
    id: uuid.UUID
    product_type: ProductType
    collected_at: date
    quantity: Decimal
    unit: FeedUnit
    hive_id: uuid.UUID | None
    apiary_id: uuid.UUID | None
    price_per_unit: Decimal | None
    total_value: Decimal | None
    notes: str | None


# ---------- movement ----------

class MoveRequest(_Clean):
    to_apiary_id: uuid.UUID
    movement_date: date | None = None
    reason: str | None = Field(default=None, max_length=255)
    new_hive_number: str | None = Field(default=None, max_length=24)
    notes: str | None = Text

    @field_validator("movement_date")
    @classmethod
    def _date(cls, v):
        return not_in_future(v, "Дата перемещения")

    @field_validator("new_hive_number")
    @classmethod
    def _num(cls, v):
        return _hive_number(v) if v else None


class MovementOut(BaseModel):
    id: uuid.UUID
    hive_id: uuid.UUID
    from_apiary: str
    to_apiary: str
    movement_date: date
    reason: str | None
    performed_by: str | None


# ---------- swarm / split / merge ----------

class _NewHive(_Clean):
    new_hive_number: str | None = Field(default=None, max_length=24)

    @field_validator("new_hive_number")
    @classmethod
    def _num(cls, v):
        return _hive_number(v) if v else None


class SwarmCreate(_NewHive):
    swarm_date: date | None = None
    swarm_count: int = Field(default=1, ge=1, le=20)
    captured: bool = False
    settle_into_hive_id: uuid.UUID | None = None
    queen_id: uuid.UUID | None = None
    actions: str | None = Text
    notes: str | None = Text

    @field_validator("swarm_date")
    @classmethod
    def _date(cls, v):
        return not_in_future(v, "Дата роения")

    @model_validator(mode="after")
    def _settle(self):
        if (self.settle_into_hive_id or self.new_hive_number) and not self.captured:
            raise ValueError("Посадить в улей можно только пойманный рой")
        if self.settle_into_hive_id and self.new_hive_number:
            raise ValueError("Выберите одно: существующий пустой улей или новый номер")
        if self.queen_id and not (self.settle_into_hive_id or self.new_hive_number):
            raise ValueError("Матку можно указать, только если рой посажен в улей")
        return self


class SplitCreate(_NewHive):
    split_date: date | None = None
    target_hive_id: uuid.UUID | None = None
    queen_id: uuid.UUID | None = None
    strength: FamilyStrength = FamilyStrength.WEAK
    notes: str | None = Text

    @field_validator("split_date")
    @classmethod
    def _date(cls, v):
        return not_in_future(v, "Дата разделения")

    @model_validator(mode="after")
    def _target(self):
        if bool(self.target_hive_id) == bool(self.new_hive_number):
            raise ValueError("Укажите номер нового улья или выберите пустой улей")
        return self


class MergeCreate(_NewHive):
    source_hive_ids: list[uuid.UUID] = Field(min_length=2, max_length=10)
    target_hive_id: uuid.UUID | None = None
    keep_queen_id: uuid.UUID | None = None
    merge_date: date | None = None
    notes: str | None = Text

    @field_validator("merge_date")
    @classmethod
    def _date(cls, v):
        return not_in_future(v, "Дата объединения")

    @model_validator(mode="after")
    def _check(self):
        if len(set(self.source_hive_ids)) != len(self.source_hive_ids):
            raise ValueError("Улей указан дважды")
        if bool(self.target_hive_id) == bool(self.new_hive_number):
            raise ValueError("Выберите улей, в который объединяем, или укажите номер нового улья")
        return self


# ---------- wintering ----------

_SEASON = re.compile(r"^(\d{4})/(\d{4})$")


class WinteringStart(_Clean):
    season: str
    pre_winter_strength: FamilyStrength | None = None
    food_kg: Decimal | None = Field(default=None, ge=0, le=Decimal("200"), decimal_places=2)
    frames_count: int | None = Field(default=None, ge=0, le=60)
    queen_condition: str | None = Field(default=None, max_length=120)
    pre_winter_treatment: str | None = Field(default=None, max_length=255)
    winter_location: str | None = Field(default=None, max_length=255)
    start_date: date | None = None
    notes: str | None = Text

    @field_validator("season")
    @classmethod
    def _season(cls, v):
        m = _SEASON.match(v or "")
        if not m or int(m.group(2)) != int(m.group(1)) + 1:
            raise ValueError("Сезон зимовки в формате 2026/2027")
        return v

    @field_validator("start_date")
    @classmethod
    def _date(cls, v):
        return not_in_future(v, "Дата начала зимовки")


class WinteringFinish(_Clean):
    end_date: date | None = None
    spring_strength: FamilyStrength | None = None
    result: WinteringResult
    notes: str | None = Text

    @field_validator("end_date")
    @classmethod
    def _date(cls, v):
        return not_in_future(v, "Дата окончания зимовки")


class WinteringOut(ORMModel):
    id: uuid.UUID
    hive_id: uuid.UUID
    season: str
    pre_winter_strength: FamilyStrength | None
    food_kg: Decimal | None
    frames_count: int | None
    queen_condition: str | None
    pre_winter_treatment: str | None
    winter_location: str | None
    start_date: date
    end_date: date | None
    spring_strength: FamilyStrength | None
    result: WinteringResult | None
    notes: str | None
