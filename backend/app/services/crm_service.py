"""Stage 7 CRM: customers, expenses, sales with payments, orders, debts and money summaries.

Nothing is deleted: customers are archived, expenses / sales / orders are cancelled with a reason.
Every write is audited. Income is counted by sale date (accrual); cash received by payment date.
"""
import uuid
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import extract, func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Apiary, Hive, User
from app.models.crm import Customer, Expense, Order, OrderItem, Payment, Sale, SaleItem
from app.models.enums import ORDER_STATUS_ORDER, FeedUnit, OrderStatus, SaleCategory
from app.models.operations import HoneyHarvest
from app.schemas.common import today
from app.schemas.crm import (
    AmountByKey,
    CrmSummary,
    CustomerBrief,
    CustomerDetails,
    CustomerIn,
    CustomerOut,
    CustomerUpdate,
    DebtorOut,
    DeliverIn,
    ExpenseIn,
    ExpenseOut,
    ExpenseUpdate,
    LineIn,
    LineOut,
    OrderCreate,
    OrderOut,
    OrderUpdate,
    PaymentIn,
    PaymentOut,
    PayNow,
    SaleCreate,
    SaleOut,
    SaleUpdate,
)
from app.services import audit_service as audit
from app.utils.errors import ConflictError, NotFoundError, ValidationFailed
from app.utils.labels import EXPENSE_CATEGORY, SALE_CATEGORY

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def _q(v: Decimal) -> Decimal:
    return Decimal(v).quantize(CENT)


def _get(db: Session, model, obj_id: uuid.UUID, message: str):
    obj = db.get(model, obj_id)
    if obj is None:
        raise NotFoundError(message)
    return obj


# ---------- money helpers ----------

def sale_total(s: Sale) -> Decimal:
    return _q(sum((i.total for i in s.items), ZERO))


def sale_paid(s: Sale) -> Decimal:
    return _q(sum((p.amount for p in s.payments), ZERO))


def sale_state(s: Sale) -> str:
    if s.cancelled_at:
        return "cancelled"
    total, paid = sale_total(s), sale_paid(s)
    return "paid" if paid >= total else "partial" if paid > 0 else "unpaid"


def _brief(c: Customer | None) -> CustomerBrief | None:
    return CustomerBrief(id=c.id, name=c.name, phone=c.phone) if c else None


def _line_out(i) -> LineOut:
    return LineOut(id=i.id, category=i.category, quantity=i.quantity, unit=i.unit,
                   price_per_unit=i.price_per_unit, total=i.total, description=i.description)


def sale_out(s: Sale) -> SaleOut:
    total, paid = sale_total(s), sale_paid(s)
    return SaleOut(
        id=s.id, sale_date=s.sale_date, customer=_brief(s.customer), order_id=s.order_id, notes=s.notes,
        items=[_line_out(i) for i in s.items],
        payments=[PaymentOut(id=p.id, sale_id=p.sale_id, paid_at=p.paid_at, amount=p.amount, method=p.method,
                             notes=p.notes) for p in s.payments],
        total=total, paid=paid, debt=ZERO if s.cancelled_at else max(total - paid, ZERO), state=sale_state(s),
        cancelled_at=s.cancelled_at, cancel_reason=s.cancel_reason, author=s.author.display_name if s.author else None, created_at=s.created_at,
    )


# ---------- customers ----------

def get_customer(db: Session, customer_id: uuid.UUID) -> Customer:
    return _get(db, Customer, customer_id, "Клиент не найден")


def _customer_sales(db: Session, customer_ids: list[uuid.UUID] | None = None) -> dict[uuid.UUID, list[Sale]]:
    stmt = select(Sale).where(Sale.customer_id.is_not(None), Sale.cancelled_at.is_(None))
    if customer_ids is not None:
        stmt = stmt.where(Sale.customer_id.in_(customer_ids))
    out: dict[uuid.UUID, list[Sale]] = defaultdict(list)
    for s in db.scalars(stmt).unique():
        out[s.customer_id].append(s)
    return out


def customer_out(c: Customer, sales: list[Sale]) -> CustomerOut:
    bought = _q(sum((sale_total(s) for s in sales), ZERO))
    paid = _q(sum((sale_paid(s) for s in sales), ZERO))
    return CustomerOut(
        id=c.id, name=c.name, phone=c.phone, city=c.city, notes=c.notes, is_archived=c.is_archived,
        created_at=c.created_at, bought=bought, paid=paid, debt=max(bought - paid, ZERO), sales_count=len(sales),
        last_purchase=max((s.sale_date for s in sales), default=None),
    )


def list_customers(db: Session, q: str | None, include_archived: bool) -> list[CustomerOut]:
    stmt = select(Customer)
    if not include_archived:
        stmt = stmt.where(Customer.is_archived.is_(False))
    if q:
        like = f"%{q.strip()}%"
        digits = "".join(ch for ch in q if ch.isdigit())
        conds = [Customer.name.ilike(like), Customer.city.ilike(like)]
        if digits:
            conds.append(Customer.phone.like(f"%{digits}%"))
        stmt = stmt.where(or_(*conds))
    customers = list(db.scalars(stmt.order_by(Customer.name)))
    sales = _customer_sales(db, [c.id for c in customers])
    return [customer_out(c, sales.get(c.id, [])) for c in customers]


def customer_details(db: Session, c: Customer) -> CustomerDetails:
    sales = list(db.scalars(select(Sale).where(Sale.customer_id == c.id)
                            .order_by(Sale.sale_date.desc(), Sale.created_at.desc())).unique())
    orders = list(db.scalars(select(Order).where(Order.customer_id == c.id)
                             .order_by(Order.order_date.desc(), Order.created_at.desc())).unique())
    base = customer_out(c, [s for s in sales if not s.cancelled_at])
    return CustomerDetails(**base.model_dump(), orders=[order_out(o) for o in orders], sales=[sale_out(s) for s in sales])


def _check_duplicate_phone(db: Session, phone: str | None, exclude: uuid.UUID | None = None) -> None:
    if not phone:
        return
    stmt = select(Customer).where(Customer.phone == phone, Customer.is_archived.is_(False))
    if exclude:
        stmt = stmt.where(Customer.id != exclude)
    clash = db.scalars(stmt).first()
    if clash:
        raise ConflictError(f"Телефон {phone} уже записан у клиента «{clash.name}»")


def create_customer(db: Session, data: CustomerIn, user: User) -> Customer:
    _check_duplicate_phone(db, data.phone)
    c = Customer(**data.model_dump(), created_by=user.id)
    db.add(c)
    db.flush()
    audit.record(db, user=user, entity_type="customer", entity_id=c.id, action="created", new=audit.snapshot(c))
    db.commit()
    db.refresh(c)
    return c


def update_customer(db: Session, c: Customer, data: CustomerUpdate, user: User) -> Customer:
    changes = data.model_dump(exclude_unset=True)
    if "name" in changes and not changes["name"]:
        raise ValidationFailed("Имя клиента не может быть пустым")
    if changes.get("phone"):
        _check_duplicate_phone(db, changes["phone"], exclude=c.id)
    before = audit.snapshot(c)
    for k, v in changes.items():
        setattr(c, k, v)
    old, new = audit.diff(before, audit.snapshot(c))
    if new:
        action = "archived" if new.get("is_archived") is True else "restored" if new.get("is_archived") is False else "updated"
        audit.record(db, user=user, entity_type="customer", entity_id=c.id, action=action, old=old, new=new)
    db.commit()
    db.refresh(c)
    return c


def _active_customer(db: Session, customer_id: uuid.UUID | None) -> Customer | None:
    if customer_id is None:
        return None
    c = get_customer(db, customer_id)
    if c.is_archived:
        raise ConflictError(f"Клиент «{c.name}» в архиве. Верните его из архива, чтобы записать продажу или заказ.")
    return c


# ---------- expenses ----------

def expense_out(e: Expense) -> ExpenseOut:
    return ExpenseOut(
        id=e.id, expense_date=e.expense_date, category=e.category, amount=e.amount, description=e.description,
        apiary_id=e.apiary_id, apiary_name=e.apiary.name if e.apiary else None, hive_id=e.hive_id,
        cancelled_at=e.cancelled_at, cancel_reason=e.cancel_reason,
        author=e.author.display_name if e.author else None, created_at=e.created_at,
    )


def _check_place(db: Session, apiary_id: uuid.UUID | None, hive_id: uuid.UUID | None) -> uuid.UUID | None:
    if hive_id:
        hive = _get(db, Hive, hive_id, "Улей не найден")
        return apiary_id or hive.apiary_id
    if apiary_id:
        _get(db, Apiary, apiary_id, "Пасека не найдена")
    return apiary_id


def create_expense(db: Session, data: ExpenseIn, user: User) -> Expense:
    apiary_id = _check_place(db, data.apiary_id, data.hive_id)
    e = Expense(expense_date=data.expense_date or today(), category=data.category, amount=data.amount,
                description=data.description, apiary_id=apiary_id, hive_id=data.hive_id, created_by=user.id)
    db.add(e)
    db.flush()
    audit.record(db, user=user, entity_type="expense", entity_id=e.id, hive_id=e.hive_id, action="created",
                 new=audit.snapshot(e, ["expense_date", "category", "amount", "description"]))
    db.commit()
    db.refresh(e)
    return e


def get_expense(db: Session, expense_id: uuid.UUID) -> Expense:
    return _get(db, Expense, expense_id, "Расход не найден")


def update_expense(db: Session, e: Expense, data: ExpenseUpdate, user: User) -> Expense:
    if e.cancelled_at:
        raise ConflictError("Расход отменён — его нельзя изменить")
    changes = data.model_dump(exclude_unset=True, exclude={"comment"})
    if "apiary_id" in changes:
        _check_place(db, changes["apiary_id"], None)
    fields = ["expense_date", "category", "amount", "description", "apiary_id"]
    before = audit.snapshot(e, fields)
    for k, v in changes.items():
        if v is not None or k in ("description", "apiary_id"):
            setattr(e, k, v)
    old, new = audit.diff(before, audit.snapshot(e, fields))
    if new:
        audit.record(db, user=user, entity_type="expense", entity_id=e.id, hive_id=e.hive_id, action="corrected",
                     old=old, new=new, comment=data.comment)
    db.commit()
    db.refresh(e)
    return e


def cancel_expense(db: Session, e: Expense, reason: str, user: User) -> Expense:
    if e.cancelled_at:
        raise ConflictError("Расход уже отменён")
    e.cancelled_at, e.cancel_reason = datetime.now(UTC), reason
    audit.record(db, user=user, entity_type="expense", entity_id=e.id, hive_id=e.hive_id, action="cancelled",
                 new={"amount": str(e.amount)}, comment=reason)
    db.commit()
    db.refresh(e)
    return e


def _period_filter(column, year: int | None, month: int | None):
    conds = []
    if year:
        conds.append(extract("year", column) == year)
    if month:
        conds.append(extract("month", column) == month)
    return conds


def list_expenses(db: Session, year: int | None, month: int | None, category, include_cancelled: bool) -> list[Expense]:
    stmt = select(Expense).where(*_period_filter(Expense.expense_date, year, month))
    if category:
        stmt = stmt.where(Expense.category == category)
    if not include_cancelled:
        stmt = stmt.where(Expense.cancelled_at.is_(None))
    return list(db.scalars(stmt.order_by(Expense.expense_date.desc(), Expense.created_at.desc()).limit(500)).unique())


# ---------- sales & payments ----------

def get_sale(db: Session, sale_id: uuid.UUID) -> Sale:
    return _get(db, Sale, sale_id, "Продажа не найдена")


def _add_lines(db: Session, model, parent_field: str, parent_id: uuid.UUID, items: list[LineIn]) -> None:
    for line in items:
        db.add(model(**{parent_field: parent_id}, **line.model_dump()))
    db.flush()


def _initial_payment(pay: PayNow, total: Decimal) -> Decimal:
    if pay.payment == "full":
        return total
    if pay.payment == "credit":
        return ZERO
    if pay.paid_amount > total:
        raise ValidationFailed(f"Оплата ({pay.paid_amount}) больше суммы продажи ({total})")
    return pay.paid_amount


def _make_sale(db: Session, *, sale_date: date, customer: Customer | None, items: list[LineIn], notes: str | None,
               pay: PayNow, user: User, order: Order | None = None) -> Sale:
    s = Sale(sale_date=sale_date, customer_id=customer.id if customer else None, notes=notes,
             order_id=order.id if order else None, created_by=user.id)
    db.add(s)
    db.flush()
    _add_lines(db, SaleItem, "sale_id", s.id, items)
    db.refresh(s)
    total = sale_total(s)
    paid = _initial_payment(pay, total)
    if paid > 0:
        db.add(Payment(sale_id=s.id, paid_at=sale_date, amount=paid, method=pay.method, created_by=user.id))
    audit.record(db, user=user, entity_type="sale", entity_id=s.id, action="created",
                 new={"total": str(total), "paid": str(paid), "customer": customer.name if customer else None,
                      "lines": _lines_text(items)})
    return s


def create_sale(db: Session, data: SaleCreate, user: User) -> Sale:
    customer = _active_customer(db, data.customer_id)
    if data.payment != "full" and customer is None:
        raise ValidationFailed("Продажа в долг или с частичной оплатой — выберите клиента, чтобы знать, кто должен")
    s = _make_sale(db, sale_date=data.sale_date or today(), customer=customer, items=data.items, notes=data.notes,
                   pay=data, user=user)
    db.commit()
    db.refresh(s)
    return s


def update_sale(db: Session, s: Sale, data: SaleUpdate, user: User) -> Sale:
    if s.cancelled_at:
        raise ConflictError("Продажа отменена — её нельзя изменить")
    changes = data.model_dump(exclude_unset=True, exclude={"comment"})
    if "customer_id" in changes:
        if changes["customer_id"] is None and sale_paid(s) < sale_total(s):
            raise ValidationFailed("У продажи есть долг — клиента убрать нельзя")
        _active_customer(db, changes["customer_id"])
    fields = ["sale_date", "customer_id", "notes"]
    before = audit.snapshot(s, fields)
    for k, v in changes.items():
        if k == "sale_date" and v is None:
            continue
        setattr(s, k, v)
    old, new = audit.diff(before, audit.snapshot(s, fields))
    if new:
        audit.record(db, user=user, entity_type="sale", entity_id=s.id, action="corrected", old=old, new=new,
                     comment=data.comment)
    db.commit()
    db.refresh(s)
    return s


def add_payment(db: Session, s: Sale, data: PaymentIn, user: User) -> Sale:
    if s.cancelled_at:
        raise ConflictError("Продажа отменена — оплату записать нельзя")
    debt = sale_total(s) - sale_paid(s)
    if debt <= 0:
        raise ConflictError("Продажа уже полностью оплачена")
    if data.amount > debt:
        raise ValidationFailed(f"Оплата ({data.amount}) больше долга ({debt})")
    paid_at = data.paid_at or today()
    if paid_at < s.sale_date:
        raise ValidationFailed("Дата оплаты раньше даты продажи")
    p = Payment(sale_id=s.id, paid_at=paid_at, amount=data.amount, method=data.method, notes=data.notes,
                created_by=user.id)
    db.add(p)
    db.flush()
    audit.record(db, user=user, entity_type="sale", entity_id=s.id, action="payment",
                 new={"amount": str(data.amount), "method": data.method.value, "debt_left": str(debt - data.amount)})
    db.commit()
    db.refresh(s)
    return s


def cancel_sale(db: Session, s: Sale, reason: str, user: User, *, via_order: bool = False) -> Sale:
    if s.cancelled_at:
        raise ConflictError("Продажа уже отменена")
    if s.payments:
        raise ConflictError("По продаже уже есть оплата — её нельзя отменить. Возврат денег запишите как расход.")
    if s.order_id and not via_order:
        raise ConflictError("Продажа создана по заказу — отмените заказ, продажа отменится вместе с ним")
    s.cancelled_at, s.cancel_reason = datetime.now(UTC), reason
    audit.record(db, user=user, entity_type="sale", entity_id=s.id, action="cancelled",
                 new={"total": str(sale_total(s))}, comment=reason)
    if not via_order:
        db.commit()
        db.refresh(s)
    return s


def list_sales(db: Session, year: int | None, month: int | None, customer_id: uuid.UUID | None,
               unpaid: bool, include_cancelled: bool) -> list[Sale]:
    stmt = select(Sale).where(*_period_filter(Sale.sale_date, year, month))
    if customer_id:
        stmt = stmt.where(Sale.customer_id == customer_id)
    if not include_cancelled or unpaid:
        stmt = stmt.where(Sale.cancelled_at.is_(None))
    sales = list(db.scalars(stmt.order_by(Sale.sale_date.desc(), Sale.created_at.desc()).limit(500)).unique())
    if unpaid:
        sales = [s for s in sales if sale_paid(s) < sale_total(s)]
    return sales


# ---------- orders ----------

def order_total(o: Order) -> Decimal:
    return _q(sum((i.total for i in o.items), ZERO))


def order_out(o: Order) -> OrderOut:
    sale = o.sale
    return OrderOut(
        id=o.id, customer=_brief(o.customer), order_date=o.order_date, due_date=o.due_date, status=o.status,
        notes=o.notes, cancel_reason=o.cancel_reason, items=[_line_out(i) for i in o.items], total=order_total(o),
        overdue=bool(o.due_date and o.due_date < today() and o.status in (OrderStatus.NEW, OrderStatus.READY)),
        sale_id=sale.id if sale else None, sale_state=sale_state(sale) if sale else None,
        sale_debt=max(sale_total(sale) - sale_paid(sale), ZERO) if sale and not sale.cancelled_at else None,
        created_at=o.created_at,
    )


def _lines_text(items) -> list[str]:
    return [f"{SALE_CATEGORY[i.category]} {i.quantity} × {i.price_per_unit}" for i in items]


def get_order(db: Session, order_id: uuid.UUID) -> Order:
    return _get(db, Order, order_id, "Заказ не найден")


def create_order(db: Session, data: OrderCreate, user: User) -> Order:
    customer = _active_customer(db, data.customer_id)
    order_date = data.order_date or today()
    if data.due_date and data.due_date < order_date:
        raise ValidationFailed("Срок выдачи раньше даты заказа")
    o = Order(customer_id=customer.id, order_date=order_date, due_date=data.due_date, notes=data.notes,
              status=OrderStatus.NEW, created_by=user.id)
    db.add(o)
    db.flush()
    _add_lines(db, OrderItem, "order_id", o.id, data.items)
    db.refresh(o)
    audit.record(db, user=user, entity_type="order", entity_id=o.id, action="created",
                 new={"customer": customer.name, "total": str(order_total(o))})
    db.commit()
    db.refresh(o)
    return o


def _ensure_open(o: Order) -> None:
    if o.status in (OrderStatus.DELIVERED, OrderStatus.CANCELLED):
        raise ConflictError(f"Заказ уже {'выдан' if o.status == OrderStatus.DELIVERED else 'отменён'}")


def update_order(db: Session, o: Order, data: OrderUpdate, user: User) -> Order:
    _ensure_open(o)
    changes = data.model_dump(exclude_unset=True)
    old, new = {}, {}
    if "status" in changes and changes["status"]:
        target = OrderStatus(changes["status"])
        if ORDER_STATUS_ORDER[target] < ORDER_STATUS_ORDER[o.status]:
            raise ConflictError("Статус заказа нельзя вернуть назад")
        if target != o.status:
            old["status"], new["status"] = o.status.value, target.value
            o.status = target
    if "due_date" in changes:
        if changes["due_date"] and changes["due_date"] < o.order_date:
            raise ValidationFailed("Срок выдачи раньше даты заказа")
        if changes["due_date"] != o.due_date:
            old["due_date"] = o.due_date.isoformat() if o.due_date else None
            new["due_date"] = changes["due_date"].isoformat() if changes["due_date"] else None
            o.due_date = changes["due_date"]
    if "notes" in changes and changes["notes"] != o.notes:
        old["notes"], new["notes"], o.notes = o.notes, changes["notes"], changes["notes"]
    if data.items is not None:
        old["total"] = str(order_total(o))
        old["lines"] = _lines_text(o.items)
        for i in list(o.items):
            db.delete(i)  # lines of an open order are a draft, not history; the change itself is audited
        db.flush()
        _add_lines(db, OrderItem, "order_id", o.id, data.items)
        db.refresh(o)
        new["total"] = str(order_total(o))
        new["lines"] = _lines_text(o.items)
    if new:
        audit.record(db, user=user, entity_type="order", entity_id=o.id, action="updated", old=old, new=new)
    db.commit()
    db.refresh(o)
    return o


def deliver_order(db: Session, o: Order, data: DeliverIn, user: User) -> tuple[Order, Sale]:
    _ensure_open(o)
    customer = _active_customer(db, o.customer_id)
    sale_date = data.sale_date or today()
    if sale_date < o.order_date:
        raise ValidationFailed("Дата выдачи раньше даты заказа")
    lines = [LineIn(category=i.category, quantity=i.quantity, unit=i.unit, price_per_unit=i.price_per_unit,
                    description=i.description) for i in o.items]
    s = _make_sale(db, sale_date=sale_date, customer=customer, items=lines, notes=o.notes, pay=data, user=user, order=o)
    o.status = OrderStatus.DELIVERED
    audit.record(db, user=user, entity_type="order", entity_id=o.id, action="delivered",
                 new={"sale_id": str(s.id), "total": str(order_total(o))})
    db.commit()
    db.refresh(o)
    db.refresh(s)
    return o, s


def cancel_order(db: Session, o: Order, reason: str, user: User) -> Order:
    if o.status == OrderStatus.CANCELLED:
        raise ConflictError("Заказ уже отменён")
    if o.status == OrderStatus.DELIVERED and o.sale:
        cancel_sale(db, o.sale, reason, user, via_order=True)
    old = o.status.value
    o.status, o.cancel_reason = OrderStatus.CANCELLED, reason
    audit.record(db, user=user, entity_type="order", entity_id=o.id, action="cancelled",
                 old={"status": old}, new={"status": "CANCELLED"}, comment=reason)
    db.commit()
    db.refresh(o)
    return o


def list_orders(db: Session, status: OrderStatus | None, customer_id: uuid.UUID | None, open_only: bool) -> list[Order]:
    stmt = select(Order)
    if status:
        stmt = stmt.where(Order.status == status)
    if open_only:
        stmt = stmt.where(Order.status.in_([OrderStatus.NEW, OrderStatus.READY]))
    if customer_id:
        stmt = stmt.where(Order.customer_id == customer_id)
    # open orders by due date first, then the rest newest first
    return list(db.scalars(stmt.order_by(Order.due_date.asc().nulls_last(), Order.order_date.desc()).limit(500)).unique())


# ---------- debts ----------

def debts(db: Session) -> list[DebtorOut]:
    unpaid = list_sales(db, None, None, None, unpaid=True, include_cancelled=False)
    groups: dict[uuid.UUID | None, list[Sale]] = defaultdict(list)
    for s in unpaid:
        groups[s.customer_id].append(s)
    out = []
    for cid, sales in groups.items():
        sales.sort(key=lambda s: s.sale_date)
        outs = [sale_out(s) for s in sales]
        out.append(DebtorOut(customer=_brief(sales[0].customer), debt=_q(sum((x.debt for x in outs), ZERO)), sales=outs))
    return sorted(out, key=lambda d: -d.debt)


# ---------- summaries ----------

def _sum_lines(db: Session, year: int | None, month: int | None, extra=()) -> Decimal:
    return db.scalar(select(func.coalesce(func.sum(SaleItem.total), 0)).join(Sale, Sale.id == SaleItem.sale_id)
                     .where(Sale.cancelled_at.is_(None), *_period_filter(Sale.sale_date, year, month), *extra)) or ZERO


def income(db: Session, year: int, month: int | None = None) -> Decimal:
    return _q(_sum_lines(db, year, month))


def expenses_total(db: Session, year: int, month: int | None = None) -> Decimal:
    return _q(db.scalar(select(func.coalesce(func.sum(Expense.amount), 0))
                        .where(Expense.cancelled_at.is_(None), *_period_filter(Expense.expense_date, year, month))) or ZERO)


def by_month(db: Session, year: int) -> tuple[list[Decimal], list[Decimal]]:
    inc, exp = [ZERO] * 12, [ZERO] * 12
    for m, v in db.execute(select(extract("month", Sale.sale_date), func.sum(SaleItem.total))
                           .join(SaleItem, SaleItem.sale_id == Sale.id)
                           .where(Sale.cancelled_at.is_(None), extract("year", Sale.sale_date) == year)
                           .group_by(extract("month", Sale.sale_date))):
        inc[int(m) - 1] = _q(v)
    for m, v in db.execute(select(extract("month", Expense.expense_date), func.sum(Expense.amount))
                           .where(Expense.cancelled_at.is_(None), extract("year", Expense.expense_date) == year)
                           .group_by(extract("month", Expense.expense_date))):
        exp[int(m) - 1] = _q(v)
    return inc, exp


def income_by_category(db: Session, year: int, month: int | None = None) -> list[AmountByKey]:
    rows = db.execute(select(SaleItem.category, func.sum(SaleItem.total)).join(Sale, Sale.id == SaleItem.sale_id)
                      .where(Sale.cancelled_at.is_(None), *_period_filter(Sale.sale_date, year, month))
                      .group_by(SaleItem.category).order_by(func.sum(SaleItem.total).desc())).all()
    return [AmountByKey(key=c.value, label=SALE_CATEGORY[c], amount=_q(v)) for c, v in rows]


def expenses_by_category(db: Session, year: int, month: int | None = None) -> list[AmountByKey]:
    rows = db.execute(select(Expense.category, func.sum(Expense.amount))
                      .where(Expense.cancelled_at.is_(None), *_period_filter(Expense.expense_date, year, month))
                      .group_by(Expense.category).order_by(func.sum(Expense.amount).desc())).all()
    return [AmountByKey(key=c.value, label=EXPENSE_CATEGORY[c], amount=_q(v)) for c, v in rows]


def received(db: Session, year: int, month: int | None = None) -> Decimal:
    return _q(db.scalar(select(func.coalesce(func.sum(Payment.amount), 0))
                        .where(*_period_filter(Payment.paid_at, year, month))) or ZERO)


def honey_stock_kg(db: Session) -> Decimal:
    harvested = db.scalar(select(func.coalesce(func.sum(HoneyHarvest.weight_kg), 0))) or ZERO
    sold = db.scalar(select(func.coalesce(func.sum(SaleItem.quantity), 0)).join(Sale, Sale.id == SaleItem.sale_id)
                     .where(Sale.cancelled_at.is_(None), SaleItem.category == SaleCategory.HONEY,
                            SaleItem.unit == FeedUnit.KG)) or ZERO
    from app.services.stock_service import fed_honey_kg
    return _q(harvested - sold - fed_honey_kg(db))


def summary(db: Session, year: int, month: int | None) -> CrmSummary:
    inc, exp = income(db, year, month), expenses_total(db, year, month)
    inc_m, exp_m = by_month(db, year)
    debtors = debts(db)
    return CrmSummary(
        year=year, month=month, currency=get_settings().currency, income=inc, expenses=exp, profit=inc - exp,
        received=received(db, year, month), debts_total=_q(sum((d.debt for d in debtors), ZERO)),
        debtors=len(debtors),
        open_orders=db.scalar(select(func.count()).select_from(Order)
                              .where(Order.status.in_([OrderStatus.NEW, OrderStatus.READY]))) or 0,
        honey_stock_kg=honey_stock_kg(db), income_by_month=inc_m, expenses_by_month=exp_m,
        income_by_category=income_by_category(db, year, month), expenses_by_category=expenses_by_category(db, year, month),
    )
