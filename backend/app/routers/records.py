"""Stage 3 endpoints: inspections, diseases, treatments, feedings, timeline, tasks."""
import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import CAN_MANAGE, CAN_WRITE, CurrentUser, require_roles
from app.database import get_db
from app.models import User
from app.models.enums import TaskStatus
from app.schemas.check import HiveCheckOut
from app.schemas.health import (
    AttentionOut,
    CaseCreate,
    CaseOut,
    CaseUpdate,
    DiseaseCreate,
    DiseaseOut,
    FeedingCreate,
    FeedingOut,
    FeedingUpdate,
    InspectionCreate,
    InspectionOut,
    InspectionUpdate,
    TaskOut,
    TimelineItem,
    TreatmentCreate,
    TreatmentOut,
    TreatmentUpdate,
)
from app.schemas.hive import HiveOut
from app.services import health_service as health
from app.services import inspection_service as insp
from app.services import hive_check_service, timeline_service
from app.services.hive_service import get_hive, to_out as hive_out

router = APIRouter(prefix="/api", tags=["health"])
DB = Annotated[Session, Depends(get_db)]
Writer = Annotated[User, Depends(require_roles(*CAN_WRITE))]
Manager = Annotated[User, Depends(require_roles(*CAN_MANAGE))]


class Warning_(BaseModel):
    code: str
    message: str


class InspectionResult(BaseModel):
    inspection: InspectionOut
    hive: HiveOut
    warnings: list[Warning_]


class CaseResult(BaseModel):
    case: CaseOut
    hive: HiveOut


class TreatmentResult(BaseModel):
    treatment: TreatmentOut
    hive: HiveOut


class FeedingResult(BaseModel):
    feeding: FeedingOut
    hive: HiveOut


def _insp_out(i) -> InspectionOut:
    out = InspectionOut.model_validate(i)
    out.user_name = i.user.display_name if i.user else None
    return out


def _treat_out(t) -> TreatmentOut:
    out = TreatmentOut.model_validate(t)
    out.performed_by_name = t.performer.display_name if t.performer else None
    return out


# ---------- inspections ----------

@router.get("/hives/{hive_id}/check", response_model=HiveCheckOut)
def check_hive(hive_id: uuid.UUID, db: DB, user: CurrentUser):
    """«Проверка улья» after a scan: current state and what needs attention. Read-only."""
    return hive_check_service.check(db, get_hive(db, hive_id), user)


@router.get("/hives/{hive_id}/inspections", response_model=list[InspectionOut])
def list_inspections(hive_id: uuid.UUID, db: DB, _: CurrentUser):
    get_hive(db, hive_id)
    return [_insp_out(i) for i in insp.list_inspections(db, hive_id)]


@router.post("/hives/{hive_id}/inspections", response_model=InspectionResult, status_code=status.HTTP_201_CREATED)
def create_inspection(hive_id: uuid.UUID, body: InspectionCreate, db: DB, user: Writer):
    i, hive, warnings = insp.create_inspection(db, hive_id, body, user)
    return InspectionResult(inspection=_insp_out(i), hive=hive_out(hive), warnings=warnings)


@router.put("/inspections/{inspection_id}", response_model=InspectionResult)
def update_inspection(inspection_id: uuid.UUID, body: InspectionUpdate, db: DB, user: Writer):
    i, hive, warnings = insp.update_inspection(db, inspection_id, body, user)
    return InspectionResult(inspection=_insp_out(i), hive=hive_out(hive), warnings=warnings)


# ---------- disease catalog & cases ----------

@router.get("/diseases", response_model=list[DiseaseOut])
def list_diseases(db: DB, _: CurrentUser, include_inactive: bool = False):
    return health.list_diseases(db, include_inactive)


@router.post("/diseases", response_model=DiseaseOut, status_code=status.HTTP_201_CREATED)
def create_disease(body: DiseaseCreate, db: DB, user: Manager):
    return health.create_disease(db, body, user)


@router.get("/hives/{hive_id}/diseases", response_model=list[CaseOut])
def list_cases(hive_id: uuid.UUID, db: DB, _: CurrentUser):
    get_hive(db, hive_id)
    return health.list_cases(db, hive_id)


@router.post("/hives/{hive_id}/diseases", response_model=CaseResult, status_code=status.HTTP_201_CREATED)
def create_case(hive_id: uuid.UUID, body: CaseCreate, db: DB, user: Writer):
    case, hive = health.create_case(db, hive_id, body, user)
    return CaseResult(case=CaseOut.model_validate(case), hive=hive_out(hive))


@router.put("/disease-cases/{case_id}", response_model=CaseResult)
def update_case(case_id: uuid.UUID, body: CaseUpdate, db: DB, user: Writer):
    case, hive = health.update_case(db, case_id, body, user)
    return CaseResult(case=CaseOut.model_validate(case), hive=hive_out(hive))


# ---------- treatments ----------

@router.get("/hives/{hive_id}/treatments", response_model=list[TreatmentOut])
def list_treatments(hive_id: uuid.UUID, db: DB, _: CurrentUser):
    get_hive(db, hive_id)
    return [_treat_out(t) for t in health.list_treatments(db, hive_id)]


@router.post("/hives/{hive_id}/treatments", response_model=TreatmentResult, status_code=status.HTTP_201_CREATED)
def create_treatment(hive_id: uuid.UUID, body: TreatmentCreate, db: DB, user: Writer):
    t, hive = health.create_treatment(db, hive_id, body, user)
    return TreatmentResult(treatment=_treat_out(t), hive=hive_out(hive))


@router.put("/treatments/{treatment_id}", response_model=TreatmentResult)
def update_treatment(treatment_id: uuid.UUID, body: TreatmentUpdate, db: DB, user: Writer):
    t, hive = health.update_treatment(db, treatment_id, body, user)
    return TreatmentResult(treatment=_treat_out(t), hive=hive_out(hive))


# ---------- feedings ----------

@router.get("/hives/{hive_id}/feedings", response_model=list[FeedingOut])
def list_feedings(hive_id: uuid.UUID, db: DB, _: CurrentUser):
    get_hive(db, hive_id)
    return health.list_feedings(db, hive_id)


@router.post("/hives/{hive_id}/feedings", response_model=FeedingResult, status_code=status.HTTP_201_CREATED)
def create_feeding(hive_id: uuid.UUID, body: FeedingCreate, db: DB, user: Writer):
    f, hive = health.create_feeding(db, hive_id, body, user)
    return FeedingResult(feeding=FeedingOut.model_validate(f), hive=hive_out(hive))


@router.put("/feedings/{feeding_id}", response_model=FeedingResult)
def update_feeding(feeding_id: uuid.UUID, body: FeedingUpdate, db: DB, user: Writer):
    f, hive = health.update_feeding(db, feeding_id, body, user)
    return FeedingResult(feeding=FeedingOut.model_validate(f), hive=hive_out(hive))


# ---------- timeline, tasks, attention ----------

@router.get("/hives/{hive_id}/timeline", response_model=list[TimelineItem])
def timeline(hive_id: uuid.UUID, db: DB, _: CurrentUser):
    get_hive(db, hive_id)
    return timeline_service.hive_timeline(db, hive_id)


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(
    db: DB,
    _: CurrentUser,
    status_: Annotated[TaskStatus | None, Query(alias="status")] = TaskStatus.OPEN,
    hive_id: uuid.UUID | None = None,
    due_before: date | None = None,
):
    rows = health.list_tasks(db, status=status_, hive_id=hive_id, due_before=due_before)
    out = []
    for task, number in rows:
        item = TaskOut.model_validate(task)
        item.hive_number = number
        out.append(item)
    return out


@router.post("/tasks/{task_id}/done", response_model=TaskOut)
def complete_task(task_id: uuid.UUID, db: DB, user: Writer):
    return health.complete_task(db, task_id, user)


@router.get("/dashboard/attention", response_model=AttentionOut)
def attention(db: DB, _: CurrentUser):
    return health.attention(db)
