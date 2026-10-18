import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.models.rearing import RearingStatus
from app.schemas.common import clean_text


class RearingIn(BaseModel):
    label: str | None = Field(default=None, max_length=80)
    grafted_at: date
    cells_grafted: int = Field(gt=0, le=1000)
    mother_queen_id: uuid.UUID | None = None
    cell_builder_hive_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("label", "notes")
    @classmethod
    def _clean(cls, v):
        return clean_text(v)


class StepDoneIn(BaseModel):
    count: int | None = Field(default=None, ge=0, le=1000)


class CancelIn(BaseModel):
    reason: str = Field(min_length=1, max_length=255)


class RearingStep(BaseModel):
    key: str
    day: int
    date: date
    title: str
    hint: str
    count_field: str | None      # which count this step records (accepted, sealed, emerged, mated)
    count_label: str | None
    state: str                   # done | today | overdue | upcoming | skipped
    task_id: uuid.UUID | None


class RearingOut(BaseModel):
    id: uuid.UUID
    label: str
    grafted_at: date
    day: int                     # today = day N after grafting
    cells_grafted: int
    cells_accepted: int | None
    cells_sealed: int | None
    queens_emerged: int | None
    queens_mated: int | None
    mother_queen_id: uuid.UUID | None
    mother_queen_code: str | None
    cell_builder_hive_id: uuid.UUID | None
    cell_builder_number: str | None
    status: RearingStatus
    finished_at: datetime | None
    cancel_reason: str | None
    notes: str | None
    next_step: RearingStep | None
    steps: list[RearingStep]
