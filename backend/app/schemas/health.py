import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator

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
from app.schemas.common import ORMModel, clean_text, local_date, not_in_future, today

Text = Field(default=None, max_length=5000)
Short = Field(default=None, max_length=255)


def _clean(v):
    return clean_text(v)


# ---------- inspections ----------

class InspectionFields(BaseModel):
    inspected_at: datetime | None = None
    strength: FamilyStrength
    frames_total: int = Field(default=0, ge=0, le=60)
    brood_frames: int = Field(default=0, ge=0, le=60)
    honey_frames: int = Field(default=0, ge=0, le=60)
    pollen_frames: int = Field(default=0, ge=0, le=60)
    queen_present: bool | None = None
    queen_condition: QueenCondition | None = None
    egg_laying: bool | None = None
    queen_cells: int = Field(default=0, ge=0, le=100)
    swarming_signs: bool = False
    food_level: FoodLevel | None = None
    aggressiveness: int | None = Field(default=None, ge=1, le=5)
    health_status: InspectionHealth = InspectionHealth.HEALTHY
    next_inspection_at: date | None = None
    notes: str | None = Text

    @field_validator("notes")
    @classmethod
    def _notes(cls, v):
        return _clean(v)

    @field_validator("inspected_at")
    @classmethod
    def _when(cls, v):
        if v is None:
            return v
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v - datetime.now(timezone.utc) > timedelta(hours=14):  # beekeeper's clock may be ahead of UTC
            raise ValueError("Дата осмотра не может быть в будущем")
        return v

    @model_validator(mode="after")
    def _frames(self):
        used = self.brood_frames + self.honey_frames + self.pollen_frames
        if used > self.frames_total:
            raise ValueError(
                f"Рамок с расплодом, мёдом и пергой ({used}) больше, чем всего рамок ({self.frames_total})"
            )
        when = local_date(self.inspected_at) if self.inspected_at else today()
        if self.next_inspection_at and self.next_inspection_at < when:
            raise ValueError("Следующий осмотр не может быть раньше этого осмотра")
        return self


class InspectionCreate(InspectionFields):
    client_uid: uuid.UUID | None = None  # made by the phone (offline queue): repeated sends are ignored


class InspectionUpdate(InspectionFields):
    comment: str | None = Field(default=None, max_length=1000)


class InspectionOut(ORMModel):
    id: uuid.UUID
    hive_id: uuid.UUID
    user_name: str | None = None
    inspected_at: datetime
    strength: FamilyStrength
    frames_total: int
    brood_frames: int
    honey_frames: int
    pollen_frames: int
    queen_present: bool | None
    queen_condition: QueenCondition | None
    egg_laying: bool | None
    queen_cells: int
    swarming_signs: bool
    food_level: FoodLevel | None
    aggressiveness: int | None
    health_status: InspectionHealth
    next_inspection_at: date | None
    notes: str | None
    created_at: datetime


# ---------- diseases ----------

class DiseaseCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    is_quarantine: bool = False

    @field_validator("name")
    @classmethod
    def _name(cls, v):
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Название болезни слишком короткое")
        return v


class DiseaseOut(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    is_quarantine: bool
    is_active: bool


class CaseCreate(BaseModel):
    disease_id: uuid.UUID
    detected_at: date | None = None
    severity: DiseaseSeverity = DiseaseSeverity.MODERATE
    status: DiseaseCaseStatus = DiseaseCaseStatus.SUSPECTED
    symptoms: str | None = Text
    diagnosis: str | None = Text
    notes: str | None = Text
    resolved_at: date | None = None

    @field_validator("detected_at")
    @classmethod
    def _det(cls, v):
        return not_in_future(v, "Дата обнаружения")


class CaseUpdate(BaseModel):
    severity: DiseaseSeverity | None = None
    status: DiseaseCaseStatus | None = None
    symptoms: str | None = Text
    diagnosis: str | None = Text
    notes: str | None = Text
    resolved_at: date | None = None
    comment: str | None = Field(default=None, max_length=1000)

    @field_validator("resolved_at")
    @classmethod
    def _res(cls, v):
        return not_in_future(v, "Дата выздоровления")


class CaseOut(ORMModel):
    id: uuid.UUID
    hive_id: uuid.UUID
    disease: DiseaseOut
    detected_at: date
    severity: DiseaseSeverity
    symptoms: str | None
    diagnosis: str | None
    status: DiseaseCaseStatus
    resolved_at: date | None
    notes: str | None
    created_at: datetime


# ---------- treatments ----------

class TreatmentFields(BaseModel):
    treated_at: date | None = None
    disease_id: uuid.UUID | None = None
    hive_disease_id: uuid.UUID | None = None
    medication: str = Field(min_length=1, max_length=120)
    dosage: str | None = Field(default=None, max_length=120)
    method: str | None = Field(default=None, max_length=120)
    result: str | None = Text
    next_treatment_date: date | None = None
    notes: str | None = Text
    # medicine taken from the warehouse (both or neither)
    stock_item_id: uuid.UUID | None = None
    stock_quantity: Decimal | None = Field(default=None, gt=0, le=Decimal("100000"), decimal_places=3)

    @model_validator(mode="after")
    def _stock(self):
        if (self.stock_item_id is None) != (self.stock_quantity is None):
            raise ValueError("Для списания со склада выберите препарат и укажите количество")
        return self

    @field_validator("medication")
    @classmethod
    def _med(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Укажите препарат")
        return v

    @field_validator("treated_at")
    @classmethod
    def _date(cls, v):
        return not_in_future(v, "Дата обработки")

    @model_validator(mode="after")
    def _next(self):
        base = self.treated_at or today()
        if self.next_treatment_date and self.next_treatment_date < base:
            raise ValueError("Следующая обработка не может быть раньше этой")
        return self


class TreatmentCreate(TreatmentFields):
    client_uid: uuid.UUID | None = None  # made by the phone (offline queue): repeated sends are ignored


class TreatmentUpdate(TreatmentFields):
    comment: str | None = Field(default=None, max_length=1000)


class TreatmentOut(ORMModel):
    id: uuid.UUID
    hive_id: uuid.UUID
    disease: DiseaseOut | None
    hive_disease_id: uuid.UUID | None
    treated_at: date
    medication: str
    dosage: str | None
    method: str | None
    performed_by_name: str | None = None
    result: str | None
    next_treatment_date: date | None
    notes: str | None
    created_at: datetime
    stock_item_id: uuid.UUID | None = None
    stock_quantity: Decimal | None = None


# ---------- feedings ----------

class FeedingFields(BaseModel):
    fed_at: date | None = None
    feed_type: FeedType
    quantity: Decimal = Field(gt=0, le=Decimal("100000"), decimal_places=2)
    unit: FeedUnit
    reason: str | None = Short
    result: str | None = Text
    next_feeding_date: date | None = None
    notes: str | None = Text

    @field_validator("fed_at")
    @classmethod
    def _date(cls, v):
        return not_in_future(v, "Дата подкормки")

    @model_validator(mode="after")
    def _next(self):
        base = self.fed_at or today()
        if self.next_feeding_date and self.next_feeding_date < base:
            raise ValueError("Следующая подкормка не может быть раньше этой")
        return self


class FeedingCreate(FeedingFields):
    client_uid: uuid.UUID | None = None  # made by the phone (offline queue): repeated sends are ignored


class FeedingUpdate(FeedingFields):
    comment: str | None = Field(default=None, max_length=1000)


class FeedingOut(ORMModel):
    id: uuid.UUID
    hive_id: uuid.UUID
    fed_at: date
    feed_type: FeedType
    quantity: Decimal
    unit: FeedUnit
    reason: str | None
    result: str | None
    next_feeding_date: date | None
    notes: str | None
    created_at: datetime


# ---------- tasks, timeline, results ----------

class TaskOut(ORMModel):
    id: uuid.UUID
    hive_id: uuid.UUID | None
    hive_number: str | None = None
    kind: TaskKind
    title: str
    due_date: date
    status: TaskStatus
    completed_at: datetime | None


class TimelineItem(BaseModel):
    kind: str            # inspection | disease_opened | disease_resolved | treatment | feeding | event
    at: datetime
    title: str
    details: list[str] = []
    author: str | None = None
    ref_id: uuid.UUID | None = None
    # history events (kind == "event") carry the raw audit change for the client to describe
    action: str | None = None
    entity_type: str | None = None
    old_value: dict | None = None
    new_value: dict | None = None
    comment: str | None = None


class AttentionOut(BaseModel):
    needs_inspection: int
    open_tasks: int
    overdue_tasks: int
    sick: int
