import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CAN_MANAGE, CAN_WRITE, CurrentUser, require_roles
from app.database import get_db
from app.models import FamilyStrength, HiveStatus, User
from app.repositories import hive_repository as repo
from app.schemas.hive import (
    AuditEntryOut,
    EndFamilyRequest,
    FamilyOut,
    FamilyUpdate,
    HiveCreate,
    HiveListResponse,
    HiveOut,
    HiveUpdate,
    ReplaceFamilyRequest,
)
from app.schemas.queen import AssignQueenRequest, QueenAssignmentOut, RemoveQueenRequest
from app.services import hive_service as svc
from app.services import queen_service

router = APIRouter(prefix="/api/hives", tags=["hives"])
DB = Annotated[Session, Depends(get_db)]
Manager = Annotated[User, Depends(require_roles(*CAN_MANAGE))]
Writer = Annotated[User, Depends(require_roles(*CAN_WRITE))]


@router.get("", response_model=HiveListResponse)
def list_hives(
    db: DB,
    _: CurrentUser,
    apiary_id: uuid.UUID | None = None,
    status_: Annotated[list[HiveStatus] | None, Query(alias="status")] = None,
    strength: Annotated[list[FamilyStrength] | None, Query()] = None,
    needs_inspection: bool = False,
    q: Annotated[str | None, Query(max_length=100)] = None,
    include_archived: bool = False,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    hives, total = repo.list_hives(db, apiary_id=apiary_id, statuses=status_, strengths=strength, needs_inspection=needs_inspection, q=q,
                                   include_archived=include_archived, limit=limit, offset=offset)
    return HiveListResponse(items=[svc.to_list_item(h) for h in hives], total=total)


@router.post("", response_model=HiveOut, status_code=status.HTTP_201_CREATED)
def create_hive(body: HiveCreate, db: DB, user: Manager):
    return svc.to_out(svc.create_hive(db, body, user))


@router.get("/{hive_id}", response_model=HiveOut)
def get_hive(hive_id: uuid.UUID, db: DB, _: CurrentUser):
    return svc.to_out(svc.get_hive(db, hive_id))


@router.put("/{hive_id}", response_model=HiveOut)
def update_hive(hive_id: uuid.UUID, body: HiveUpdate, db: DB, user: Manager):
    return svc.to_out(svc.update_hive(db, svc.get_hive(db, hive_id), body, user))


@router.get("/{hive_id}/history", response_model=list[AuditEntryOut])
def hive_history(hive_id: uuid.UUID, db: DB, _: CurrentUser):
    return svc.history(db, svc.get_hive(db, hive_id))


# ---- families ----

@router.get("/{hive_id}/families", response_model=list[FamilyOut])
def list_families(hive_id: uuid.UUID, db: DB, _: CurrentUser):
    return repo.list_families(db, svc.get_hive(db, hive_id).id)


@router.post("/{hive_id}/families", response_model=HiveOut, status_code=status.HTTP_201_CREATED)
def settle_family(hive_id: uuid.UUID, body: ReplaceFamilyRequest, db: DB, user: Manager):
    """Settle a new family (the current one, if any, is closed and kept in history)."""
    return svc.to_out(svc.replace_family(db, svc.get_hive(db, hive_id), body, user))


@router.patch("/{hive_id}/family", response_model=HiveOut)
def update_family(hive_id: uuid.UUID, body: FamilyUpdate, db: DB, user: Writer):
    return svc.to_out(svc.update_family(db, svc.get_hive(db, hive_id), body, user))


@router.post("/{hive_id}/family/end", response_model=HiveOut)
def end_family(hive_id: uuid.UUID, body: EndFamilyRequest, db: DB, user: Manager):
    return svc.to_out(svc.end_family(db, svc.get_hive(db, hive_id), body, user))


# ---- queen ----

@router.get("/{hive_id}/queens", response_model=list[QueenAssignmentOut])
def hive_queen_history(hive_id: uuid.UUID, db: DB, _: CurrentUser):
    hive = svc.get_hive(db, hive_id)
    return [queen_service.assignment_out(a, hive.hive_number) for a in repo.list_hive_queen_assignments(db, hive.id)]


@router.post("/{hive_id}/queen", response_model=HiveOut)
def assign_queen(hive_id: uuid.UUID, body: AssignQueenRequest, db: DB, user: Manager):
    """Install a queen. A queen already in the hive is retired with `previous_queen_status`."""
    return svc.to_out(queen_service.assign_queen(db, svc.get_hive(db, hive_id), body, user))


@router.post("/{hive_id}/queen/remove", response_model=HiveOut)
def remove_queen(hive_id: uuid.UUID, body: RemoveQueenRequest, db: DB, user: Manager):
    return svc.to_out(svc.remove_queen(db, svc.get_hive(db, hive_id), body, user))
