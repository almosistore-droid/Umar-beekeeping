import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CAN_MANAGE, CurrentUser, require_roles
from app.database import get_db
from app.models import User
from app.repositories.hive_repository import apiary_hive_counts
from app.schemas.apiary import ApiaryCreate, ApiaryOut, ApiaryUpdate
from app.services import apiary_service as svc

router = APIRouter(prefix="/api/apiaries", tags=["apiaries"])
DB = Annotated[Session, Depends(get_db)]
Manager = Annotated[User, Depends(require_roles(*CAN_MANAGE))]


@router.get("", response_model=list[ApiaryOut])
def list_apiaries(db: DB, _: CurrentUser, include_archived: bool = False):
    return svc.list_apiaries(db, include_archived)


@router.post("", response_model=ApiaryOut, status_code=status.HTTP_201_CREATED)
def create_apiary(body: ApiaryCreate, db: DB, user: Manager):
    return svc.to_out(svc.create_apiary(db, body, user))


@router.get("/{apiary_id}", response_model=ApiaryOut)
def get_apiary(apiary_id: uuid.UUID, db: DB, _: CurrentUser):
    apiary = svc.get_apiary(db, apiary_id)
    return svc.to_out(apiary, apiary_hive_counts(db).get(apiary.id, 0))


@router.put("/{apiary_id}", response_model=ApiaryOut)
def update_apiary(apiary_id: uuid.UUID, body: ApiaryUpdate, db: DB, user: Manager):
    apiary = svc.update_apiary(db, svc.get_apiary(db, apiary_id), body, user)
    return svc.to_out(apiary, apiary_hive_counts(db).get(apiary.id, 0))
