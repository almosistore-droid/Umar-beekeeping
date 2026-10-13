"""Stage 4 endpoints: honey, products, movement, swarm, split, merge, wintering."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import CAN_MANAGE, CAN_WRITE, CurrentUser, require_roles
from app.database import get_db
from app.models import User
from app.schemas.common import today
from app.schemas.hive import HiveOut
from app.schemas.operations import (
    HarvestCreate,
    HarvestOut,
    HarvestUpdate,
    HiveHoneyOut,
    HoneyStats,
    MergeCreate,
    MoveRequest,
    MovementOut,
    ProductCreate,
    ProductOut,
    SplitCreate,
    SwarmCreate,
    WinteringFinish,
    WinteringOut,
    WinteringStart,
)
from app.services import honey_service as honey
from app.services import operations_service as ops
from app.services.hive_service import get_hive, to_out as hive_out

router = APIRouter(prefix="/api", tags=["harvest & operations"])
DB = Annotated[Session, Depends(get_db)]
Writer = Annotated[User, Depends(require_roles(*CAN_WRITE))]
Manager = Annotated[User, Depends(require_roles(*CAN_MANAGE))]


class SplitResult(BaseModel):
    source: HiveOut
    new_hive: HiveOut


class SwarmResult(BaseModel):
    hive: HiveOut
    new_hive: HiveOut | None


class WinteringResultOut(BaseModel):
    wintering: WinteringOut
    hive: HiveOut


# ---------- honey ----------

@router.get("/hives/{hive_id}/honey", response_model=HiveHoneyOut)
def hive_honey(hive_id: uuid.UUID, db: DB, _: CurrentUser, year: int | None = None):
    get_hive(db, hive_id)
    return honey.hive_honey(db, hive_id, year or today().year)


@router.post("/hives/{hive_id}/honey", response_model=HarvestOut, status_code=status.HTTP_201_CREATED)
def create_harvest(hive_id: uuid.UUID, body: HarvestCreate, db: DB, user: Writer):
    return honey.create_harvest(db, hive_id, body, user)


@router.put("/honey/{harvest_id}", response_model=HarvestOut)
def update_harvest(harvest_id: uuid.UUID, body: HarvestUpdate, db: DB, user: Writer):
    return honey.update_harvest(db, harvest_id, body, user)


@router.get("/honey/stats", response_model=HoneyStats)
def honey_stats(db: DB, _: CurrentUser, year: Annotated[int | None, Query(ge=2000, le=2200)] = None,
                apiary_id: uuid.UUID | None = None):
    return honey.stats(db, year or today().year, apiary_id)


# ---------- products ----------

@router.get("/products", response_model=list[ProductOut])
def list_products(db: DB, _: CurrentUser, year: int | None = None, hive_id: uuid.UUID | None = None):
    return honey.list_products(db, year, hive_id)


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(body: ProductCreate, db: DB, user: Writer):
    return honey.create_product(db, body, user)


# ---------- movement ----------

@router.post("/hives/{hive_id}/move", response_model=HiveOut)
def move_hive(hive_id: uuid.UUID, body: MoveRequest, db: DB, user: Manager):
    return hive_out(ops.move_hive(db, hive_id, body, user))


@router.get("/hives/{hive_id}/movements", response_model=list[MovementOut])
def movements(hive_id: uuid.UUID, db: DB, _: CurrentUser):
    get_hive(db, hive_id)
    return [MovementOut(id=m.id, hive_id=m.hive_id, from_apiary=m.from_apiary.name, to_apiary=m.to_apiary.name,
                        movement_date=m.movement_date, reason=m.reason,
                        performed_by=m.performer.display_name if m.performer else None)
            for m in ops.list_movements(db, hive_id)]


# ---------- swarm / split / merge ----------

@router.post("/hives/{hive_id}/swarms", response_model=SwarmResult, status_code=status.HTTP_201_CREATED)
def record_swarm(hive_id: uuid.UUID, body: SwarmCreate, db: DB, user: Manager):
    _, new_hive = ops.record_swarm(db, hive_id, body, user)
    return SwarmResult(hive=hive_out(get_hive(db, hive_id)), new_hive=hive_out(new_hive) if new_hive else None)


@router.post("/hives/{hive_id}/split", response_model=SplitResult, status_code=status.HTTP_201_CREATED)
def split_hive(hive_id: uuid.UUID, body: SplitCreate, db: DB, user: Manager):
    source, new_hive = ops.split_hive(db, hive_id, body, user)
    return SplitResult(source=hive_out(source), new_hive=hive_out(new_hive))


@router.post("/merges", response_model=HiveOut, status_code=status.HTTP_201_CREATED)
def merge_hives(body: MergeCreate, db: DB, user: Manager):
    return hive_out(ops.merge_hives(db, body, user))


# ---------- wintering ----------

@router.get("/hives/{hive_id}/winterings", response_model=list[WinteringOut])
def winterings(hive_id: uuid.UUID, db: DB, _: CurrentUser):
    get_hive(db, hive_id)
    return ops.list_winterings(db, hive_id)


@router.post("/hives/{hive_id}/winterings", response_model=WinteringOut, status_code=status.HTTP_201_CREATED)
def start_wintering(hive_id: uuid.UUID, body: WinteringStart, db: DB, user: Manager):
    return ops.start_wintering(db, hive_id, body, user)


@router.put("/winterings/{wintering_id}/finish", response_model=WinteringResultOut)
def finish_wintering(wintering_id: uuid.UUID, body: WinteringFinish, db: DB, user: Manager):
    w, hive = ops.finish_wintering(db, wintering_id, body, user)
    return WinteringResultOut(wintering=WinteringOut.model_validate(w), hive=hive_out(hive))
