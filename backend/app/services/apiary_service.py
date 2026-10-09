import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ARCHIVED_HIVE_STATUSES, Apiary, Hive, User
from app.repositories.hive_repository import apiary_hive_counts
from app.schemas.apiary import ApiaryCreate, ApiaryOut, ApiaryUpdate
from app.services import audit_service as audit
from app.utils.errors import ConflictError, NotFoundError


def get_apiary(db: Session, apiary_id: uuid.UUID) -> Apiary:
    apiary = db.get(Apiary, apiary_id)
    if apiary is None:
        raise NotFoundError("Пасека не найдена")
    return apiary


def to_out(apiary: Apiary, hive_count: int = 0) -> ApiaryOut:
    out = ApiaryOut.model_validate(apiary)
    out.hive_count = hive_count
    return out


def list_apiaries(db: Session, include_archived: bool = False) -> list[ApiaryOut]:
    stmt = select(Apiary).order_by(Apiary.is_archived, Apiary.name)
    if not include_archived:
        stmt = stmt.where(Apiary.is_archived.is_(False))
    counts = apiary_hive_counts(db)
    return [to_out(a, counts.get(a.id, 0)) for a in db.scalars(stmt)]


def create_apiary(db: Session, data: ApiaryCreate, user: User) -> Apiary:
    apiary = Apiary(**data.model_dump(), owner_id=user.id)
    db.add(apiary)
    db.flush()
    audit.record(db, user=user, entity_type="apiary", entity_id=apiary.id, action="created",
                 new=audit.snapshot(apiary))
    db.commit()
    return apiary


def update_apiary(db: Session, apiary: Apiary, data: ApiaryUpdate, user: User) -> Apiary:
    changes = data.model_dump(exclude_unset=True)
    if changes.get("is_archived"):
        active = db.scalar(
            select(Hive.id).where(Hive.apiary_id == apiary.id, Hive.status.not_in(ARCHIVED_HIVE_STATUSES)).limit(1)
        )
        if active:
            raise ConflictError("На пасеке есть действующие ульи. Сначала перенесите их на другую пасеку.")
    before = audit.snapshot(apiary)
    for key, value in changes.items():
        setattr(apiary, key, value)
    old, new = audit.diff(before, audit.snapshot(apiary))
    if new:
        audit.record(db, user=user, entity_type="apiary", entity_id=apiary.id, action="updated", old=old, new=new)
    db.commit()
    db.refresh(apiary)
    return apiary
