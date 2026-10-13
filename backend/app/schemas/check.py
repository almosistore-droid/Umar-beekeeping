import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.models.enums import FamilyStrength, FoodLevel, HiveStatus, InspectionHealth, QueenStatus
from app.schemas.apiary import ApiaryBrief


class CheckIssue(BaseModel):
    code: str
    level: Literal["attention", "problem"]
    message: str


class CheckQueen(BaseModel):
    id: uuid.UUID
    queen_code: str
    age_label: str | None
    status: QueenStatus


class CheckInspection(BaseModel):
    id: uuid.UUID
    inspected_at: datetime
    days_ago: int
    user_name: str | None
    strength: FamilyStrength
    frames_total: int
    brood_frames: int
    honey_frames: int
    pollen_frames: int
    queen_present: bool | None
    egg_laying: bool | None
    queen_cells: int
    swarming_signs: bool
    food_level: FoodLevel | None
    health_status: InspectionHealth


class CheckCase(BaseModel):
    disease_name: str
    status: str


class CheckTask(BaseModel):
    title: str
    due_date: date
    overdue: bool


class HiveCheckOut(BaseModel):
    """«Проверка улья»: the hive's current state and what needs attention, in one request."""
    hive_id: uuid.UUID
    hive_number: str
    apiary: ApiaryBrief
    status: HiveStatus
    is_archived: bool
    verdict: Literal["ok", "attention", "problem"]
    headline: str
    issues: list[CheckIssue]
    strength: FamilyStrength | None
    queen: CheckQueen | None
    last_inspection: CheckInspection | None
    next_inspection_at: datetime | None
    open_cases: list[CheckCase]
    open_tasks: list[CheckTask]
    honey_year_kg: Decimal
