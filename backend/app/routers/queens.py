import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import CAN_MANAGE, CurrentUser, require_roles
from app.database import get_db
from app.models import QueenStatus, User
from app.repositories import hive_repository as repo
from app.schemas.queen import QueenAssignmentOut, QueenCreate, QueenOut, QueenUpdate
from app.services import queen_service as svc

router = APIRouter(prefix="/api/queens", tags=["queens"])
DB = Annotated[Session, Depends(get_db)]
Manager = Annotated[User, Depends(require_roles(*CAN_MANAGE))]


class QueenListResponse(BaseModel):
    items: list[QueenOut]
    total: int


@router.get("", response_model=QueenListResponse)
def list_queens(
    db: DB,
    _: CurrentUser,
    status_: Annotated[list[QueenStatus] | None, Query(alias="status")] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    in_hive: bool | None = None,
    include_removed: bool = False,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    queens, total = repo.list_queens(db, statuses=status_, q=q, in_hive=in_hive,
                                     include_removed=include_removed, limit=limit, offset=offset)
    return QueenListResponse(items=svc.to_out_many(db, queens), total=total)


@router.post("", response_model=QueenOut, status_code=status.HTTP_201_CREATED)
def create_queen(body: QueenCreate, db: DB, user: Manager):
    queen = svc.create_queen(db, body, user)
    return svc.to_out_many(db, [queen])[0]


@router.get("/{queen_id}", response_model=QueenOut)
def get_queen(queen_id: uuid.UUID, db: DB, _: CurrentUser):
    return svc.to_out_many(db, [svc.get_queen(db, queen_id)])[0]


@router.put("/{queen_id}", response_model=QueenOut)
def update_queen(queen_id: uuid.UUID, body: QueenUpdate, db: DB, user: Manager):
    queen = svc.update_queen(db, svc.get_queen(db, queen_id), body, user)
    return svc.to_out_many(db, [queen])[0]


@router.get("/{queen_id}/history", response_model=list[QueenAssignmentOut])
def queen_history(queen_id: uuid.UUID, db: DB, _: CurrentUser):
    return svc.queen_history(db, svc.get_queen(db, queen_id))
