"""Honey harvests, other products and honey statistics (stage 4, user stories 1 and 5)."""
import uuid
from decimal import Decimal

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.models import Apiary, Hive, HoneyHarvest, OtherProduct, User
from app.schemas.common import today
from app.schemas.operations import HarvestCreate, HarvestUpdate, HiveRank, ProductCreate
from app.services import audit_service as audit
from app.services.health_service import get_hive_for_record
from app.utils.errors import NotFoundError, ValidationFailed

ZERO = Decimal("0")


def _next_number(db: Session, hive_id: uuid.UUID, year: int) -> int:
    # Lock the hive row so two harvests saved at the same moment cannot get the same number
    db.execute(select(Hive.id).where(Hive.id == hive_id).with_for_update())
    current = db.scalar(select(func.max(HoneyHarvest.harvest_number))
                        .where(HoneyHarvest.hive_id == hive_id, HoneyHarvest.harvest_year == year))
    return (current or 0) + 1


def create_harvest(db: Session, hive_id: uuid.UUID, data: HarvestCreate, user: User) -> HoneyHarvest:
    hive = get_hive_for_record(db, hive_id, require_family=False)
    when = data.harvest_date or today()
    harvest = HoneyHarvest(hive_id=hive.id, apiary_id=hive.apiary_id, harvest_date=when, harvest_year=when.year,
                           harvest_number=_next_number(db, hive.id, when.year), created_by=user.id,
                           **data.model_dump(exclude={"harvest_date"}))
    db.add(harvest)
    db.commit()
    db.refresh(harvest)
    return harvest


def update_harvest(db: Session, harvest_id: uuid.UUID, data: HarvestUpdate, user: User) -> HoneyHarvest:
    harvest = db.get(HoneyHarvest, harvest_id)
    if harvest is None:
        raise NotFoundError("Откачка не найдена")
    fields = ["harvest_date", "honey_type", "frames_count", "weight_kg", "price_per_kg", "notes"]
    values = data.model_dump(exclude={"comment"})
    values["harvest_date"] = values["harvest_date"] or harvest.harvest_date
    if values["harvest_date"].year != harvest.harvest_year:
        raise ValidationFailed("Дату откачки можно исправить только в пределах того же года")
    before = audit.snapshot(harvest, fields)
    for k in fields:
        setattr(harvest, k, values[k])
    old, new = audit.diff(before, audit.snapshot(harvest, fields))
    if new:
        audit.record(db, user=user, entity_type="honey_harvest", entity_id=harvest.id, hive_id=harvest.hive_id,
                     action="corrected", old=old, new=new, comment=data.comment)
    db.commit()
    db.refresh(harvest)
    return harvest


def hive_honey(db: Session, hive_id: uuid.UUID, year: int) -> dict:
    items = list(db.scalars(select(HoneyHarvest).where(HoneyHarvest.hive_id == hive_id)
                            .order_by(HoneyHarvest.harvest_date.desc(), HoneyHarvest.harvest_number.desc())).unique())
    this_year = [h for h in items if h.harvest_year == year]
    return {
        "items": items, "year": year,
        "year_kg": sum((h.weight_kg for h in this_year), ZERO),
        "year_value": sum((h.total_value or ZERO for h in this_year), ZERO),
        "all_time_kg": sum((h.weight_kg for h in items), ZERO),
    }


def stats(db: Session, year: int, apiary_id: uuid.UUID | None = None) -> dict:
    base = select(HoneyHarvest)
    if apiary_id:
        base = base.where(HoneyHarvest.apiary_id == apiary_id)
    sub = base.subquery()

    def total(*conds) -> Decimal:
        return db.scalar(select(func.coalesce(func.sum(sub.c.weight_kg), 0)).where(*conds)) or ZERO

    t = today()
    year_kg = total(sub.c.harvest_year == year)
    month_kg = total(sub.c.harvest_year == t.year, extract("month", sub.c.harvest_date) == t.month) \
        if year == t.year else ZERO
    all_time = total()
    year_value = db.scalar(select(func.coalesce(func.sum(sub.c.total_value), 0))
                           .where(sub.c.harvest_year == year)) or ZERO

    by_month = [ZERO] * 12
    for month, kg in db.execute(select(extract("month", sub.c.harvest_date), func.sum(sub.c.weight_kg))
                                .where(sub.c.harvest_year == year).group_by(extract("month", sub.c.harvest_date))):
        by_month[int(month) - 1] = kg

    rank_rows = db.execute(
        select(Hive.id, Hive.hive_number, Apiary.name, func.sum(sub.c.weight_kg), func.count())
        .select_from(sub).join(Hive, Hive.id == sub.c.hive_id).join(Apiary, Apiary.id == Hive.apiary_id)
        .where(sub.c.harvest_year == year)
        .group_by(Hive.id, Hive.hive_number, Apiary.name)
        .order_by(func.sum(sub.c.weight_kg).desc(), Hive.hive_number)
    ).all()
    by_hive = [HiveRank(hive_id=r[0], hive_number=r[1], apiary_name=r[2], kg=r[3], harvests=r[4]) for r in rank_rows]
    producing = len(by_hive)
    return {
        "year": year, "month_kg": month_kg, "year_kg": year_kg, "season_kg": year_kg, "all_time_kg": all_time,
        "year_value": year_value, "producing_hives": producing,
        "avg_per_hive_kg": (year_kg / producing).quantize(Decimal("0.01")) if producing else ZERO,
        "best_hive": by_hive[0] if by_hive else None, "by_month": by_month, "by_hive": by_hive,
    }


def year_kg_by_hive(db: Session, year: int) -> dict[uuid.UUID, Decimal]:
    rows = db.execute(select(HoneyHarvest.hive_id, func.sum(HoneyHarvest.weight_kg))
                      .where(HoneyHarvest.harvest_year == year).group_by(HoneyHarvest.hive_id)).all()
    return dict(rows)


# ---------- other products ----------

def create_product(db: Session, data: ProductCreate, user: User) -> OtherProduct:
    apiary_id = data.apiary_id
    if data.hive_id:
        hive = db.get(Hive, data.hive_id)
        if hive is None:
            raise NotFoundError("Улей не найден")
        apiary_id = apiary_id or hive.apiary_id
    if apiary_id and db.get(Apiary, apiary_id) is None:
        raise NotFoundError("Пасека не найдена")
    values = data.model_dump(exclude={"collected_at", "apiary_id"})
    product = OtherProduct(collected_at=data.collected_at or today(), apiary_id=apiary_id, created_by=user.id, **values)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def list_products(db: Session, year: int | None, hive_id: uuid.UUID | None = None) -> list[OtherProduct]:
    stmt = select(OtherProduct).order_by(OtherProduct.collected_at.desc(), OtherProduct.created_at.desc())
    if year:
        stmt = stmt.where(extract("year", OtherProduct.collected_at) == year)
    if hive_id:
        stmt = stmt.where(OtherProduct.hive_id == hive_id)
    return list(db.scalars(stmt).unique())
