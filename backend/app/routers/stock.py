"""Warehouse: everyone signed in sees it; assistants record receipts, use and frame preparation;
items, inventory counts, cancellations and norms belong to ADMIN / BEEKEEPER."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CAN_MANAGE, CAN_WRITE, get_current_user, require_roles
from app.database import get_db
from app.models import User
from app.schemas.stock import (
    CancelIn,
    FramePrepIn,
    FramePrepOut,
    FramePrepResult,
    MovementIn,
    NormsIn,
    NormsOut,
    StockItemDetails,
    StockItemIn,
    StockItemOut,
    StockItemUpdate,
    StockOverview,
)
from app.services import stock_service as svc
from app.services.crm_service import honey_stock_kg
from app.utils.errors import PermissionDenied

router = APIRouter(prefix="/api/stock", tags=["stock"])
DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
Writer = Annotated[User, Depends(require_roles(*CAN_WRITE))]
Manager = Annotated[User, Depends(require_roles(*CAN_MANAGE))]


@router.get("", response_model=StockOverview)
def overview(db: DB, _: CurrentUser, archived: Annotated[bool, Query()] = False):
    items = svc.list_items(db, include_archived=archived)
    norms = svc.get_norms(db)
    db.commit()  # system items / norms may have just been created
    return StockOverview(items=items, honey_kg=honey_stock_kg(db), norms=NormsOut.model_validate(norms))


@router.get("/norms", response_model=NormsOut)
def get_norms(db: DB, _: CurrentUser):
    norms = svc.get_norms(db)
    db.commit()
    return norms


@router.put("/norms", response_model=NormsOut)
def put_norms(body: NormsIn, db: DB, user: Manager):
    return svc.update_norms(db, body, user)


@router.post("/items", response_model=StockItemOut, status_code=status.HTTP_201_CREATED)
def create_item(body: StockItemIn, db: DB, user: Manager):
    return svc.create_item(db, body, user)


@router.get("/items/{item_id}", response_model=StockItemDetails)
def item(item_id: uuid.UUID, db: DB, _: CurrentUser):
    out, movements = svc.item_details(db, item_id)
    return StockItemDetails(item=out, movements=movements)


@router.put("/items/{item_id}", response_model=StockItemOut)
def update_item(item_id: uuid.UUID, body: StockItemUpdate, db: DB, user: Manager):
    return svc.update_item(db, item_id, body, user)


@router.post("/items/{item_id}/archive", response_model=StockItemOut)
def archive_item(item_id: uuid.UUID, db: DB, user: Manager):
    return svc.set_archived(db, item_id, True, user)


@router.post("/items/{item_id}/restore", response_model=StockItemOut)
def restore_item(item_id: uuid.UUID, db: DB, user: Manager):
    return svc.set_archived(db, item_id, False, user)


@router.post("/items/{item_id}/movements", response_model=StockItemOut, status_code=status.HTTP_201_CREATED)
def add_movement(item_id: uuid.UUID, body: MovementIn, db: DB, user: Writer):
    if body.kind == "INVENTORY" and user.role not in CAN_MANAGE:
        raise PermissionDenied("Пересчёт склада делает пчеловод или администратор")
    return svc.add_movement(db, item_id, body, user)


@router.post("/movements/{movement_id}/cancel", response_model=StockItemOut)
def cancel_movement(movement_id: uuid.UUID, body: CancelIn, db: DB, user: Manager):
    return svc.cancel_movement(db, movement_id, body.reason, user)


@router.get("/frame-preps", response_model=list[FramePrepOut])
def frame_preps(db: DB, _: CurrentUser):
    return svc.list_frame_preps(db)


@router.post("/frame-preps", response_model=FramePrepResult, status_code=status.HTTP_201_CREATED)
def prepare_frames(body: FramePrepIn, db: DB, user: Writer):
    prep, lines = svc.prepare_frames(db, body, user)
    return FramePrepResult(prep=FramePrepOut.model_validate(prep), lines=lines)


@router.post("/frame-preps/{prep_id}/cancel", response_model=FramePrepOut)
def cancel_frame_prep(prep_id: uuid.UUID, body: CancelIn, db: DB, user: Manager):
    return svc.cancel_frame_prep(db, prep_id, body.reason, user)
