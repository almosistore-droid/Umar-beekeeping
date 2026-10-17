"""Warehouse: items, movements, frame preparation and the automatic write-offs of feedings and treatments.

- Balance = Σ movements that are not cancelled (never stored).
- Manual movements: receipt (+), consumption (− and not more than there is), inventory (sets the real count).
- Frame preparation by the norms: wire and foundation per frame, empty frames −, ready frames +.
- A feeding writes off its feed by the norms (syrup → sugar); a treatment writes off the chosen medicine.
  When the record is corrected the old write-off is cancelled and a new one is made, so history stays.
- Automatic write-offs may take a balance below zero (the record itself must never be refused);
  such an item is shown as low.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Feeding, Hive, Treatment, User
from app.models.enums import FeedType, FeedUnit
from app.models.stock import (
    CANDY,
    FOUNDATION,
    FRAMES_EMPTY,
    FRAMES_READY,
    MANUAL_KINDS,
    PROTEIN,
    SUGAR,
    WIRE,
    FramePreparation,
    StockCategory,
    StockItem,
    StockMovement,
    StockMovementKind,
    StockNorms,
    StockUnit,
)
from app.schemas.common import today
from app.schemas.stock import (
    FramePrepIn,
    MovementIn,
    MovementOut,
    NormsIn,
    StockItemIn,
    StockItemOut,
    StockItemUpdate,
    UseLine,
)
from app.services import audit_service as audit
from app.utils.errors import ConflictError, NotFoundError, ValidationFailed

ZERO = Decimal("0")
Q3 = Decimal("0.001")

# code, name, category, unit — the calculations rely on these units, so they cannot be changed
SYSTEM_ITEMS = (
    (FRAMES_EMPTY, "Рамки пустые", StockCategory.FRAMES, StockUnit.PCS),
    (FRAMES_READY, "Рамки с вощиной", StockCategory.FRAMES, StockUnit.PCS),
    (FOUNDATION, "Вощина", StockCategory.FRAMES, StockUnit.KG),
    (WIRE, "Проволока", StockCategory.FRAMES, StockUnit.M),
    (SUGAR, "Сахар", StockCategory.FEED, StockUnit.KG),
    (CANDY, "Канди", StockCategory.FEED, StockUnit.KG),
    (PROTEIN, "Белковый корм", StockCategory.FEED, StockUnit.KG),
)
UNIT_LABEL = {StockUnit.PCS: "шт", StockUnit.KG: "кг", StockUnit.G: "г", StockUnit.L: "л", StockUnit.ML: "мл",
              StockUnit.M: "м", StockUnit.PACK: "уп."}


def q3(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Q3, rounding=ROUND_HALF_UP)


def fmt(value: Decimal) -> str:
    """1.260 → «1,26»: for Russian messages."""
    text = format(q3(value).normalize(), "f")
    return text.replace(".", ",")


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------- system items and norms ----------

def ensure_system(db: Session) -> None:
    """The items and norms the calculations need (created by migration 0012; recreated if missing)."""
    db.execute(insert(StockItem).values([
        {"id": uuid.uuid4(), "code": code, "name": name, "category": cat, "unit": unit}
        for code, name, cat, unit in SYSTEM_ITEMS
    ]).on_conflict_do_nothing(index_elements=["code"], index_where=StockItem.code.is_not(None)))
    db.execute(insert(StockNorms).values(id=uuid.uuid4(), singleton=True, wire_m_per_frame=Decimal("3"),
                                         foundation_g_per_frame=Decimal("110"), sugar_kg_per_l_syrup=Decimal("0.63"),
                                         sugar_kg_per_kg_syrup=Decimal("0.5"))
               .on_conflict_do_nothing(index_elements=["singleton"]))
    db.flush()


def get_norms(db: Session) -> StockNorms:
    norms = db.scalar(select(StockNorms))
    if norms is None:
        ensure_system(db)
        norms = db.scalar(select(StockNorms))
    return norms


def update_norms(db: Session, data: NormsIn, user: User) -> StockNorms:
    norms = get_norms(db)
    fields = list(NormsIn.model_fields)
    before = audit.snapshot(norms, fields)
    for k in fields:
        setattr(norms, k, getattr(data, k))
    norms.updated_by = user.id
    old, new = audit.diff(before, audit.snapshot(norms, fields))
    if new:
        audit.record(db, user=user, entity_type="stock_norms", entity_id=norms.id, action="updated", old=old, new=new)
    db.commit()
    db.refresh(norms)
    return norms


def system_item(db: Session, code: str) -> StockItem:
    item = db.scalar(select(StockItem).where(StockItem.code == code))
    if item is None:
        ensure_system(db)
        item = db.scalar(select(StockItem).where(StockItem.code == code))
    return item


# ---------- balances ----------

def balances(db: Session, item_ids: list[uuid.UUID] | None = None) -> dict[uuid.UUID, Decimal]:
    stmt = (select(StockMovement.item_id, func.coalesce(func.sum(StockMovement.quantity), 0))
            .where(StockMovement.cancelled_at.is_(None)).group_by(StockMovement.item_id))
    if item_ids is not None:
        stmt = stmt.where(StockMovement.item_id.in_(item_ids))
    return {item_id: q3(total) for item_id, total in db.execute(stmt)}


def balance(db: Session, item_id: uuid.UUID) -> Decimal:
    return balances(db, [item_id]).get(item_id, ZERO)


def is_low(item: StockItem, quantity: Decimal) -> bool:
    return quantity < 0 or (item.min_quantity is not None and quantity < item.min_quantity)


def item_out(item: StockItem, quantity: Decimal) -> StockItemOut:
    out = StockItemOut.model_validate(item)
    out.quantity = quantity
    out.low = not item.is_archived and is_low(item, quantity)
    return out


_CATEGORY_ORDER = {StockCategory.FRAMES: 0, StockCategory.FEED: 1, StockCategory.MEDICINE: 2, StockCategory.OTHER: 3}
_SYSTEM_ORDER = {code: i for i, (code, *_rest) in enumerate(SYSTEM_ITEMS)}


def list_items(db: Session, include_archived: bool = False) -> list[StockItemOut]:
    ensure_system(db)
    stmt = select(StockItem)
    if not include_archived:
        stmt = stmt.where(StockItem.is_archived.is_(False))
    items = list(db.scalars(stmt))
    items.sort(key=lambda i: (i.is_archived, _CATEGORY_ORDER[i.category], _SYSTEM_ORDER.get(i.code, 99), i.name.lower()))
    bal = balances(db)
    return [item_out(i, bal.get(i.id, ZERO)) for i in items]


def low_items(db: Session) -> list[StockItemOut]:
    return [i for i in list_items(db) if i.low]


# ---------- items ----------

def get_item(db: Session, item_id: uuid.UUID) -> StockItem:
    item = db.get(StockItem, item_id)
    if item is None:
        raise NotFoundError("Позиция склада не найдена")
    return item


def _name_taken(db: Session, name: str, except_id: uuid.UUID | None = None) -> bool:
    stmt = select(StockItem.id).where(func.lower(StockItem.name) == name.lower(), StockItem.is_archived.is_(False))
    if except_id:
        stmt = stmt.where(StockItem.id != except_id)
    return db.scalar(stmt) is not None


def create_item(db: Session, data: StockItemIn, user: User) -> StockItemOut:
    if _name_taken(db, data.name):
        raise ConflictError(f"На складе уже есть «{data.name}»")
    item = StockItem(name=data.name, category=data.category, unit=data.unit, min_quantity=data.min_quantity,
                     notes=data.notes, created_by=user.id)
    db.add(item)
    db.flush()
    audit.record(db, user=user, entity_type="stock_item", entity_id=item.id, action="created",
                 new=audit.snapshot(item, ["name", "category", "unit", "min_quantity"]))
    if data.initial_quantity:
        _move(db, item, StockMovementKind.RECEIPT, data.initial_quantity, user, note="Начальный остаток")
    db.commit()
    db.refresh(item)
    return item_out(item, balance(db, item.id))


def update_item(db: Session, item_id: uuid.UUID, data: StockItemUpdate, user: User) -> StockItemOut:
    item = get_item(db, item_id)
    if item.is_archived:
        raise ConflictError("Позиция в архиве — сначала верните её")
    if _name_taken(db, data.name, item.id):
        raise ConflictError(f"На складе уже есть «{data.name}»")
    fields = ["name", "category", "unit", "min_quantity", "notes"]
    if item.code and (data.unit != item.unit or data.category != item.category):
        raise ConflictError("У этой позиции нельзя менять единицу и раздел: по ней считаются нормы")
    if data.unit != item.unit and db.scalar(select(func.count()).select_from(StockMovement)
                                           .where(StockMovement.item_id == item.id)):
        raise ConflictError("Единицу нельзя менять: по позиции уже есть движения")
    before = audit.snapshot(item, fields)
    for k in fields:
        setattr(item, k, getattr(data, k))
    old, new = audit.diff(before, audit.snapshot(item, fields))
    if new:
        audit.record(db, user=user, entity_type="stock_item", entity_id=item.id, action="updated", old=old, new=new)
    db.commit()
    db.refresh(item)
    return item_out(item, balance(db, item.id))


def set_archived(db: Session, item_id: uuid.UUID, archived: bool, user: User) -> StockItemOut:
    item = get_item(db, item_id)
    if item.code:
        raise ConflictError("Эта позиция нужна для расчётов и не убирается в архив")
    if item.is_archived == archived:
        return item_out(item, balance(db, item.id))
    if not archived and _name_taken(db, item.name, item.id):
        raise ConflictError(f"На складе уже есть «{item.name}»")
    item.is_archived = archived
    audit.record(db, user=user, entity_type="stock_item", entity_id=item.id,
                 action="archived" if archived else "restored", new={"name": item.name})
    db.commit()
    db.refresh(item)
    return item_out(item, balance(db, item.id))


# ---------- movements ----------

def _move(db: Session, item: StockItem, kind: StockMovementKind, quantity: Decimal, user: User | None, *,
          moved_at=None, note: str | None = None, hive_id: uuid.UUID | None = None, **links) -> StockMovement:
    movement = StockMovement(item_id=item.id, kind=kind, quantity=q3(quantity), moved_at=moved_at or today(),
                             note=note, created_by=user.id if user else None, **links)
    db.add(movement)
    db.flush()
    # no hive_id: the feeding / treatment itself is in the hive's timeline; this is the warehouse log
    audit.record(db, user=user, entity_type="stock_movement", entity_id=movement.id,
                 action=kind.value.lower(),
                 new={"item": item.name, "quantity": str(movement.quantity), "unit": item.unit.value})
    return movement


def add_movement(db: Session, item_id: uuid.UUID, data: MovementIn, user: User) -> StockItemOut:
    item = get_item(db, item_id)
    if item.is_archived:
        raise ConflictError("Позиция в архиве — сначала верните её")
    current = balance(db, item.id)
    unit = UNIT_LABEL[item.unit]
    if data.kind == "INVENTORY":
        delta = q3(data.quantity) - current
        if delta == 0:
            raise ValidationFailed(f"На складе уже {fmt(current)} {unit} — менять нечего")
        _move(db, item, StockMovementKind.INVENTORY, delta, user, moved_at=data.moved_at,
              note=data.note or f"Пересчёт: было {fmt(current)} {unit}, стало {fmt(data.quantity)} {unit}")
    else:
        if data.quantity <= 0:
            raise ValidationFailed("Количество должно быть больше нуля")
        if data.kind == "CONSUMPTION":
            if data.quantity > current:
                raise ConflictError(f"На складе только {fmt(current)} {unit} — столько списать нельзя")
            _move(db, item, StockMovementKind.CONSUMPTION, -data.quantity, user, moved_at=data.moved_at, note=data.note)
        else:
            _move(db, item, StockMovementKind.RECEIPT, data.quantity, user, moved_at=data.moved_at, note=data.note)
    db.commit()
    return item_out(item, balance(db, item.id))


def _cancel(db: Session, movement: StockMovement, user: User | None, reason: str, hive_id=None) -> None:
    movement.cancelled_at = _now()
    audit.record(db, user=user, entity_type="stock_movement", entity_id=movement.id,
                 action="cancelled", old={"quantity": str(movement.quantity)},
                 new={"item": movement.item.name, "unit": movement.item.unit.value}, comment=reason)


def cancel_movement(db: Session, movement_id: uuid.UUID, reason: str, user: User) -> StockItemOut:
    movement = db.get(StockMovement, movement_id)
    if movement is None:
        raise NotFoundError("Запись склада не найдена")
    if movement.cancelled_at:
        raise ConflictError("Эта запись уже отменена")
    if movement.kind not in MANUAL_KINDS:
        raise ConflictError("Эта запись сделана автоматически — исправьте подкормку, обработку или подготовку рамок")
    _cancel(db, movement, user, reason.strip())
    db.commit()
    return item_out(movement.item, balance(db, movement.item_id))


def item_details(db: Session, item_id: uuid.UUID, limit: int = 200) -> tuple[StockItemOut, list[MovementOut]]:
    item = get_item(db, item_id)
    rows = list(db.scalars(select(StockMovement).where(StockMovement.item_id == item.id)
                           .order_by(StockMovement.moved_at.desc(), StockMovement.created_at.desc()).limit(limit)))
    feeding_ids = [m.feeding_id for m in rows if m.feeding_id]
    treatment_ids = [m.treatment_id for m in rows if m.treatment_id]
    hive_of: dict[uuid.UUID, uuid.UUID] = {}
    if feeding_ids:
        hive_of.update({k: v for k, v in db.execute(select(Feeding.id, Feeding.hive_id).where(Feeding.id.in_(feeding_ids)))})
    if treatment_ids:
        hive_of.update({k: v for k, v in db.execute(select(Treatment.id, Treatment.hive_id)
                                                    .where(Treatment.id.in_(treatment_ids)))})
    numbers = {k: v for k, v in db.execute(select(Hive.id, Hive.hive_number)
                                           .where(Hive.id.in_(set(hive_of.values()))))} if hive_of else {}
    out = []
    for m in rows:
        mo = MovementOut.model_validate(m)
        mo.author_name = m.author.display_name if m.author else None
        hive_id = hive_of.get(m.feeding_id or m.treatment_id) if (m.feeding_id or m.treatment_id) else None
        if hive_id:
            mo.hive_id, mo.hive_number = hive_id, numbers.get(hive_id)
        out.append(mo)
    return item_out(item, balance(db, item.id)), out


# ---------- frame preparation ----------

@dataclass
class _Use:
    item: StockItem
    quantity: Decimal


def _lines(db: Session, uses: list[_Use]) -> list[UseLine]:
    bal = balances(db, [u.item.id for u in uses])
    return [UseLine(item_id=u.item.id, name=u.item.name, unit=u.item.unit, quantity=q3(u.quantity),
                    balance_after=bal.get(u.item.id, ZERO)) for u in uses]


def prepare_frames(db: Session, data: FramePrepIn, user: User) -> tuple[FramePreparation, list[UseLine]]:
    norms = get_norms(db)
    prep = FramePreparation(prepared_at=data.prepared_at or today(), frames=data.frames,
                            wire_m_per_frame=norms.wire_m_per_frame, foundation_g_per_frame=norms.foundation_g_per_frame,
                            notes=data.notes, created_by=user.id)
    db.add(prep)
    db.flush()
    n = Decimal(data.frames)
    plan = [
        (WIRE, -n * norms.wire_m_per_frame),
        (FOUNDATION, -n * norms.foundation_g_per_frame / 1000),
        (FRAMES_EMPTY, -n),
        (FRAMES_READY, n),
    ]
    uses = []
    for code, qty in plan:
        if q3(qty) == 0:
            continue
        item = system_item(db, code)
        _move(db, item, StockMovementKind.FRAME_PREP, qty, user, moved_at=prep.prepared_at,
              note=f"Подготовка рамок: {data.frames} шт", frame_prep_id=prep.id)
        uses.append(_Use(item, qty))
    audit.record(db, user=user, entity_type="frame_prep", entity_id=prep.id, action="frames_prepared",
                 new={"frames": data.frames, "wire_m_per_frame": str(prep.wire_m_per_frame),
                      "foundation_g_per_frame": str(prep.foundation_g_per_frame)})
    db.commit()
    db.refresh(prep)
    return prep, _lines(db, uses)


def list_frame_preps(db: Session, limit: int = 50) -> list[FramePreparation]:
    return list(db.scalars(select(FramePreparation).order_by(FramePreparation.prepared_at.desc(),
                                                             FramePreparation.created_at.desc()).limit(limit)).unique())


def cancel_frame_prep(db: Session, prep_id: uuid.UUID, reason: str, user: User) -> FramePreparation:
    prep = db.get(FramePreparation, prep_id)
    if prep is None:
        raise NotFoundError("Запись о подготовке рамок не найдена")
    if prep.cancelled_at:
        raise ConflictError("Эта запись уже отменена")
    prep.cancelled_at = _now()
    for m in db.scalars(select(StockMovement).where(StockMovement.frame_prep_id == prep.id,
                                                    StockMovement.cancelled_at.is_(None))):
        m.cancelled_at = prep.cancelled_at
    audit.record(db, user=user, entity_type="frame_prep", entity_id=prep.id, action="cancelled",
                 old={"frames": prep.frames}, comment=reason.strip())
    db.commit()
    db.refresh(prep)
    return prep


# ---------- feedings and treatments ----------

_MASS_TO_KG = {FeedUnit.KG: Decimal("1"), FeedUnit.G: Decimal("0.001")}
_FEED_ITEM = {FeedType.CANDY: CANDY, FeedType.PROTEIN: PROTEIN, FeedType.POLLEN_SUBSTITUTE: PROTEIN}


def feeding_need(norms: StockNorms, feed_type: FeedType, quantity: Decimal, unit: FeedUnit) -> tuple[str, Decimal] | None:
    """Which system item a feeding uses and how much of it (in the item's unit), or None.

    Syrup → sugar: litres × «sugar per litre of syrup», kilograms × «sugar per kg of syrup».
    Candy and protein feed in kg/g → the same kilograms. Honey is counted in the honey stock
    (harvested − sold − fed), medicated and other feed are not tracked automatically.
    """
    if feed_type == FeedType.SUGAR_SYRUP:
        if unit in (FeedUnit.L, FeedUnit.ML):
            litres = quantity / (1000 if unit == FeedUnit.ML else 1)
            return SUGAR, litres * norms.sugar_kg_per_l_syrup
        if unit in _MASS_TO_KG:
            return SUGAR, quantity * _MASS_TO_KG[unit] * norms.sugar_kg_per_kg_syrup
        return None
    code = _FEED_ITEM.get(feed_type)
    if code and unit in _MASS_TO_KG:
        return code, quantity * _MASS_TO_KG[unit]
    return None


def _active_link(db: Session, **link) -> StockMovement | None:
    (column, value), = link.items()
    return db.scalar(select(StockMovement).where(getattr(StockMovement, column) == value,
                                                 StockMovement.cancelled_at.is_(None)))


def _sync(db: Session, link: dict, item: StockItem | None, quantity: Decimal | None, kind: StockMovementKind,
          moved_at, note: str, hive_id: uuid.UUID, user: User) -> None:
    current = _active_link(db, **link)
    want = q3(-quantity) if item is not None and quantity and q3(quantity) != 0 else None
    if current is not None and want is not None and current.item_id == item.id and current.quantity == want:
        if current.moved_at != moved_at:
            current.moved_at = moved_at
        return
    if current is not None:
        _cancel(db, current, user, "Запись исправлена", hive_id=hive_id)
    if want is not None:
        _move(db, item, kind, want, user, moved_at=moved_at, note=note, hive_id=hive_id, **link)


def sync_feeding(db: Session, feeding: Feeding, hive: Hive, user: User) -> None:
    need = feeding_need(get_norms(db), feeding.feed_type, feeding.quantity, feeding.unit)
    item, qty = (system_item(db, need[0]), need[1]) if need else (None, None)
    _sync(db, {"feeding_id": feeding.id}, item, qty, StockMovementKind.FEEDING, feeding.fed_at,
          f"Подкормка, улей №{hive.hive_number}", hive.id, user)


def treatment_stock(db: Session, treatment_id: uuid.UUID) -> StockMovement | None:
    return _active_link(db, treatment_id=treatment_id)


def check_treatment_item(db: Session, item_id: uuid.UUID | None) -> StockItem | None:
    if item_id is None:
        return None
    item = get_item(db, item_id)
    if item.is_archived:
        raise ConflictError(f"«{item.name}» в архиве склада")
    return item


def sync_treatment(db: Session, treatment: Treatment, hive: Hive, item: StockItem | None,
                   quantity: Decimal | None, user: User) -> None:
    _sync(db, {"treatment_id": treatment.id}, item, quantity, StockMovementKind.TREATMENT, treatment.treated_at,
          f"Обработка, улей №{hive.hive_number}", hive.id, user)


def fed_honey_kg(db: Session) -> Decimal:
    """Honey given back to the bees (feedings in kg / g) — taken off the honey stock."""
    total = ZERO
    for unit, factor in _MASS_TO_KG.items():
        q = db.scalar(select(func.coalesce(func.sum(Feeding.quantity), 0))
                      .where(Feeding.feed_type == FeedType.HONEY, Feeding.unit == unit)) or ZERO
        total += Decimal(q) * factor
    return q3(total)
