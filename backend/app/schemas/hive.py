import re
import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import (
    FamilyOrigin,
    FamilyStatus,
    FamilyStrength,
    HiveStatus,
    HiveType,
)
from app.schemas.apiary import ApiaryBrief
from app.schemas.common import ORMModel, clean_text, not_in_future
from app.schemas.queen import QueenBrief

_NUMBER_RE = re.compile(r"^[0-9A-Za-zА-Яа-яЁё][0-9A-Za-zА-Яа-яЁё\-/.]{0,19}$")


def _hive_number(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip().lstrip("№#").strip()
    if not _NUMBER_RE.match(v):
        raise ValueError("Номер улья: до 20 символов — цифры, буквы, «-», «/» или «.»")
    return v


# ---------- families ----------

class FamilyCreate(BaseModel):
    strength: FamilyStrength = FamilyStrength.MEDIUM
    origin: FamilyOrigin = FamilyOrigin.OTHER
    start_date: date | None = None
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("start_date")
    @classmethod
    def _start(cls, v):
        return not_in_future(v, "Дата заселения семьи")


class ReplaceFamilyRequest(FamilyCreate):
    # What happened to the previous family
    previous_status: FamilyStatus = FamilyStatus.REPLACED
    end_reason: str | None = Field(default=None, max_length=255)
    comment: str | None = Field(default=None, max_length=1000)

    @field_validator("previous_status")
    @classmethod
    def _prev(cls, v):
        if v == FamilyStatus.ACTIVE:
            raise ValueError("Прежняя семья не может остаться активной")
        return v


class EndFamilyRequest(BaseModel):
    status: FamilyStatus
    end_date: date | None = None
    end_reason: str | None = Field(default=None, max_length=255)

    @field_validator("status")
    @classmethod
    def _status(cls, v):
        if v == FamilyStatus.ACTIVE:
            raise ValueError("Выберите, что случилось с семьёй")
        return v

    @field_validator("end_date")
    @classmethod
    def _end(cls, v):
        return not_in_future(v, "Дата")


class FamilyUpdate(BaseModel):
    strength: FamilyStrength | None = None
    notes: str | None = Field(default=None, max_length=5000)
    comment: str | None = Field(default=None, max_length=1000)


class FamilyOut(ORMModel):
    id: uuid.UUID
    hive_id: uuid.UUID
    strength: FamilyStrength
    status: FamilyStatus
    origin: FamilyOrigin
    start_date: date
    end_date: date | None
    end_reason: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


# ---------- hives ----------

class HiveCreate(BaseModel):
    apiary_id: uuid.UUID
    hive_number: str = Field(min_length=1, max_length=24)
    hive_type: HiveType = HiveType.DADANT
    status: HiveStatus | None = None
    installation_date: date | None = None
    colonization_date: date | None = None
    next_inspection_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=5000)
    family: FamilyCreate | None = None
    queen_id: uuid.UUID | None = None

    @field_validator("hive_number")
    @classmethod
    def _num(cls, v):
        return _hive_number(v)

    @field_validator("installation_date")
    @classmethod
    def _inst(cls, v):
        return not_in_future(v, "Дата установки улья")

    @field_validator("colonization_date")
    @classmethod
    def _col(cls, v):
        return not_in_future(v, "Дата заселения")

    @field_validator("notes")
    @classmethod
    def _notes(cls, v):
        return clean_text(v)

    @field_validator("status")
    @classmethod
    def _status(cls, v):
        if v in (HiveStatus.MERGED, HiveStatus.SPLIT, HiveStatus.SOLD, HiveStatus.LOST):
            raise ValueError("Новый улей не может быть сразу объединённым, разделённым, проданным или потерянным")
        return v

    @model_validator(mode="after")
    def _consistency(self):
        if self.queen_id and not self.family:
            raise ValueError("Чтобы подсадить матку, укажите пчелиную семью")
        if self.status == HiveStatus.EMPTY and self.family:
            raise ValueError("Пустой улей не может иметь семью")
        return self


class HiveUpdate(BaseModel):
    hive_number: str | None = Field(default=None, min_length=1, max_length=24)
    hive_type: HiveType | None = None
    status: HiveStatus | None = None
    installation_date: date | None = None
    colonization_date: date | None = None
    next_inspection_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=5000)
    # Optimistic concurrency: send the version you loaded; 409 if someone changed it since
    version: int | None = Field(default=None, ge=1)
    comment: str | None = Field(default=None, max_length=1000)

    @field_validator("hive_number")
    @classmethod
    def _num(cls, v):
        return _hive_number(v)

    @field_validator("installation_date")
    @classmethod
    def _inst(cls, v):
        return not_in_future(v, "Дата установки улья")

    @field_validator("colonization_date")
    @classmethod
    def _col(cls, v):
        return not_in_future(v, "Дата заселения")

    @field_validator("status")
    @classmethod
    def _status(cls, v):
        if v in (HiveStatus.MERGED, HiveStatus.SPLIT):
            raise ValueError("Объединение и разделение выполняются отдельной операцией")
        return v


class HiveOut(ORMModel):
    id: uuid.UUID
    apiary: ApiaryBrief
    hive_number: str
    hive_type: HiveType
    status: HiveStatus
    is_archived: bool
    installation_date: date | None
    colonization_date: date | None
    last_inspection_at: datetime | None
    next_inspection_at: datetime | None
    notes: str | None
    version: int
    current_family: FamilyOut | None
    current_queen: QueenBrief | None
    created_at: datetime
    updated_at: datetime


class HiveListItem(BaseModel):
    id: uuid.UUID
    apiary: ApiaryBrief
    hive_number: str
    hive_type: HiveType
    status: HiveStatus
    is_archived: bool
    strength: FamilyStrength | None
    queen_code: str | None
    queen_age_label: str | None
    last_inspection_at: datetime | None
    next_inspection_at: datetime | None


class HiveListResponse(BaseModel):
    items: list[HiveListItem]
    total: int


# ---------- history ----------

class AuditEntryOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    user_name: str | None
    entity_type: str
    entity_id: uuid.UUID
    action: str
    old_value: dict | None
    new_value: dict | None
    comment: str | None
