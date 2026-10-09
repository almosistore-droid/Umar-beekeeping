import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import REMOVED_QUEEN_STATUSES, QueenOrigin, QueenStatus
from app.schemas.common import ORMModel, clean_text, not_in_future, today

Score = Field(default=None, ge=1, le=5)

# International queen marking colours by last digit of the birth year
MARKING_COLORS = {1: "WHITE", 6: "WHITE", 2: "YELLOW", 7: "YELLOW", 3: "RED", 8: "RED",
                  4: "GREEN", 9: "GREEN", 5: "BLUE", 0: "BLUE"}


class QueenFields(BaseModel):
    birth_date: date | None = None
    birth_year: int | None = Field(default=None, ge=1990, le=2200)
    breed: str | None = Field(default=None, max_length=80)
    origin: QueenOrigin | None = None
    egg_laying_quality: int | None = Score
    swarming_tendency: int | None = Score
    temperament: int | None = Score
    marking_color: str | None = Field(default=None, max_length=20)
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("birth_date")
    @classmethod
    def _birth_date(cls, v):
        return not_in_future(v, "Дата рождения матки")

    @field_validator("birth_year")
    @classmethod
    def _birth_year(cls, v):
        if v is not None and v > today().year:
            raise ValueError("Год рождения матки не может быть в будущем")
        return v

    @field_validator("breed", "notes", "marking_color")
    @classmethod
    def _clean(cls, v):
        return clean_text(v)

    @model_validator(mode="after")
    def _year_matches_date(self):
        if self.birth_date and self.birth_year and self.birth_date.year != self.birth_year:
            raise ValueError("Год рождения не совпадает с датой рождения")
        if self.birth_date and not self.birth_year:
            self.birth_year = self.birth_date.year
        return self


class QueenCreate(QueenFields):
    queen_code: str = Field(min_length=1, max_length=40, description="Например M-105")
    origin: QueenOrigin = QueenOrigin.UNKNOWN
    status: QueenStatus = QueenStatus.ACTIVE
    # Optionally install the new queen straight away
    hive_id: uuid.UUID | None = None
    installed_at: date | None = None

    @field_validator("queen_code")
    @classmethod
    def _code(cls, v: str) -> str:
        v = v.strip().upper()
        if not v:
            raise ValueError("Код матки не может быть пустым")
        return v

    @field_validator("status")
    @classmethod
    def _status(cls, v):
        if v in REMOVED_QUEEN_STATUSES:
            raise ValueError("Новая матка не может быть сразу выбывшей")
        return v

    @field_validator("installed_at")
    @classmethod
    def _installed(cls, v):
        return not_in_future(v, "Дата подсадки")


class QueenUpdate(QueenFields):
    queen_code: str | None = Field(default=None, min_length=1, max_length=40)
    status: QueenStatus | None = None
    comment: str | None = Field(default=None, max_length=1000)

    @field_validator("queen_code")
    @classmethod
    def _code(cls, v):
        return v.strip().upper() if v else v


class HiveRef(BaseModel):
    id: uuid.UUID
    hive_number: str
    apiary_name: str


class QueenOut(ORMModel):
    id: uuid.UUID
    queen_code: str
    birth_date: date | None
    birth_year: int | None
    age_months: int | None
    age_label: str | None
    breed: str | None
    origin: QueenOrigin
    status: QueenStatus
    current_hive: HiveRef | None
    installed_at: date | None
    removed_at: date | None
    removal_reason: str | None
    egg_laying_quality: int | None
    swarming_tendency: int | None
    temperament: int | None
    marking_color: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class QueenBrief(BaseModel):
    id: uuid.UUID
    queen_code: str
    status: QueenStatus
    birth_date: date | None
    birth_year: int | None
    age_months: int | None
    age_label: str | None
    breed: str | None
    marking_color: str | None
    installed_at: date | None


class QueenAssignmentOut(BaseModel):
    id: uuid.UUID
    queen_id: uuid.UUID
    queen_code: str
    hive_id: uuid.UUID
    hive_number: str
    installed_at: date
    removed_at: date | None
    removal_reason: str | None


class AssignQueenRequest(BaseModel):
    queen_id: uuid.UUID
    installed_at: date | None = None
    # What happened to the queen that was in the hive before, if any
    previous_queen_status: QueenStatus = QueenStatus.REPLACED
    removal_reason: str | None = Field(default=None, max_length=255)
    comment: str | None = Field(default=None, max_length=1000)

    @field_validator("installed_at")
    @classmethod
    def _date(cls, v):
        return not_in_future(v, "Дата подсадки")

    @field_validator("previous_queen_status")
    @classmethod
    def _prev(cls, v):
        if v not in REMOVED_QUEEN_STATUSES:
            raise ValueError("Укажите, что стало с прежней маткой: заменена, погибла, пропала или продана")
        return v


class RemoveQueenRequest(BaseModel):
    status: QueenStatus = Field(description="REPLACED, DEAD, LOST или SOLD")
    removed_at: date | None = None
    reason: str | None = Field(default=None, max_length=255)

    @field_validator("status")
    @classmethod
    def _status(cls, v):
        if v not in REMOVED_QUEEN_STATUSES:
            raise ValueError("Статус выбытия: заменена, погибла, пропала или продана")
        return v

    @field_validator("removed_at")
    @classmethod
    def _date(cls, v):
        return not_in_future(v, "Дата выбытия")
