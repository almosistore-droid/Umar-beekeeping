"""Queen rearing calendar: everyone signed in sees it; assistants and up record batches and steps."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CAN_MANAGE, CAN_WRITE, get_current_user, require_roles
from app.database import get_db
from app.models import User
from app.schemas.rearing import CancelIn, RearingIn, RearingOut, StepDoneIn
from app.services import rearing_service as svc

router = APIRouter(prefix="/api/rearing", tags=["rearing"])
DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
Writer = Annotated[User, Depends(require_roles(*CAN_WRITE))]
Manager = Annotated[User, Depends(require_roles(*CAN_MANAGE))]


@router.get("", response_model=list[RearingOut])
def list_batches(db: DB, _: CurrentUser, year: Annotated[int | None, Query(ge=2000, le=2100)] = None):
    return [svc.to_out(db, b) for b in svc.list_batches(db, year)]


@router.post("", response_model=RearingOut, status_code=status.HTTP_201_CREATED)
def create(body: RearingIn, db: DB, user: Writer):
    return svc.to_out(db, svc.create(db, body, user))


@router.get("/{batch_id}", response_model=RearingOut)
def get(batch_id: uuid.UUID, db: DB, _: CurrentUser):
    return svc.to_out(db, svc.get(db, batch_id))


@router.put("/{batch_id}", response_model=RearingOut)
def update(batch_id: uuid.UUID, body: RearingIn, db: DB, user: Writer):
    return svc.to_out(db, svc.update(db, batch_id, body, user))


@router.post("/{batch_id}/steps/{key}/done", response_model=RearingOut)
def step_done(batch_id: uuid.UUID, key: str, body: StepDoneIn, db: DB, user: Writer):
    return svc.to_out(db, svc.step_done(db, batch_id, key, body, user))


@router.post("/{batch_id}/finish", response_model=RearingOut)
def finish(batch_id: uuid.UUID, db: DB, user: Writer):
    return svc.to_out(db, svc.finish(db, batch_id, user))


@router.post("/{batch_id}/cancel", response_model=RearingOut)
def cancel(batch_id: uuid.UUID, body: CancelIn, db: DB, user: Manager):
    return svc.to_out(db, svc.cancel(db, batch_id, body.reason, user))
