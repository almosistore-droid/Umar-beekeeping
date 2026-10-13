"""Stage 7 CRM endpoints. Money and customers: ADMIN and BEEKEEPER only."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CAN_MANAGE, require_roles
from app.database import get_db
from app.models import User
from app.models.enums import ExpenseCategory, OrderStatus
from app.schemas.common import today
from app.schemas.crm import (
    CancelIn,
    CrmSummary,
    CustomerDetails,
    CustomerIn,
    CustomerOut,
    CustomerUpdate,
    DebtorOut,
    DeliverIn,
    ExpenseIn,
    ExpenseOut,
    ExpenseUpdate,
    OrderCreate,
    OrderOut,
    OrderUpdate,
    PaymentIn,
    SaleCreate,
    SaleOut,
    SaleUpdate,
)
from app.services import crm_service as svc
from app.services.report_service import validate_year

router = APIRouter(prefix="/api/crm", tags=["crm"])
DB = Annotated[Session, Depends(get_db)]
Manager = Annotated[User, Depends(require_roles(*CAN_MANAGE))]
Year = Annotated[int | None, Query(ge=2000, le=2100)]
Month = Annotated[int | None, Query(ge=1, le=12)]


@router.get("/settings")
def crm_settings(_: Manager) -> dict[str, str]:
    from app.config import get_settings
    return {"currency": get_settings().currency}


@router.get("/summary", response_model=CrmSummary)
def summary(db: DB, _: Manager, year: Year = None, month: Month = None):
    year = year or today().year
    validate_year(year)
    return svc.summary(db, year, month)


# ---- customers ----

@router.get("/customers", response_model=list[CustomerOut])
def list_customers(db: DB, _: Manager, q: Annotated[str | None, Query(max_length=100)] = None,
                   include_archived: bool = False):
    return svc.list_customers(db, q, include_archived)


@router.post("/customers", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(body: CustomerIn, db: DB, user: Manager):
    return svc.customer_out(svc.create_customer(db, body, user), [])


@router.get("/customers/{customer_id}", response_model=CustomerDetails)
def get_customer(customer_id: uuid.UUID, db: DB, _: Manager):
    return svc.customer_details(db, svc.get_customer(db, customer_id))


@router.put("/customers/{customer_id}", response_model=CustomerDetails)
def update_customer(customer_id: uuid.UUID, body: CustomerUpdate, db: DB, user: Manager):
    return svc.customer_details(db, svc.update_customer(db, svc.get_customer(db, customer_id), body, user))


# ---- expenses ----

@router.get("/expenses", response_model=list[ExpenseOut])
def list_expenses(db: DB, _: Manager, year: Year = None, month: Month = None, category: ExpenseCategory | None = None,
                  include_cancelled: bool = False):
    return [svc.expense_out(e) for e in svc.list_expenses(db, year, month, category, include_cancelled)]


@router.post("/expenses", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(body: ExpenseIn, db: DB, user: Manager):
    return svc.expense_out(svc.create_expense(db, body, user))


@router.put("/expenses/{expense_id}", response_model=ExpenseOut)
def update_expense(expense_id: uuid.UUID, body: ExpenseUpdate, db: DB, user: Manager):
    return svc.expense_out(svc.update_expense(db, svc.get_expense(db, expense_id), body, user))


@router.post("/expenses/{expense_id}/cancel", response_model=ExpenseOut)
def cancel_expense(expense_id: uuid.UUID, body: CancelIn, db: DB, user: Manager):
    return svc.expense_out(svc.cancel_expense(db, svc.get_expense(db, expense_id), body.reason, user))


# ---- sales ----

@router.get("/sales", response_model=list[SaleOut])
def list_sales(db: DB, _: Manager, year: Year = None, month: Month = None, customer_id: uuid.UUID | None = None,
               unpaid: bool = False, include_cancelled: bool = False):
    return [svc.sale_out(s) for s in svc.list_sales(db, year, month, customer_id, unpaid, include_cancelled)]


@router.post("/sales", response_model=SaleOut, status_code=status.HTTP_201_CREATED)
def create_sale(body: SaleCreate, db: DB, user: Manager):
    return svc.sale_out(svc.create_sale(db, body, user))


@router.get("/sales/{sale_id}", response_model=SaleOut)
def get_sale(sale_id: uuid.UUID, db: DB, _: Manager):
    return svc.sale_out(svc.get_sale(db, sale_id))


@router.put("/sales/{sale_id}", response_model=SaleOut)
def update_sale(sale_id: uuid.UUID, body: SaleUpdate, db: DB, user: Manager):
    return svc.sale_out(svc.update_sale(db, svc.get_sale(db, sale_id), body, user))


@router.post("/sales/{sale_id}/payments", response_model=SaleOut, status_code=status.HTTP_201_CREATED)
def add_payment(sale_id: uuid.UUID, body: PaymentIn, db: DB, user: Manager):
    return svc.sale_out(svc.add_payment(db, svc.get_sale(db, sale_id), body, user))


@router.post("/sales/{sale_id}/cancel", response_model=SaleOut)
def cancel_sale(sale_id: uuid.UUID, body: CancelIn, db: DB, user: Manager):
    return svc.sale_out(svc.cancel_sale(db, svc.get_sale(db, sale_id), body.reason, user))


# ---- orders ----

@router.get("/orders", response_model=list[OrderOut])
def list_orders(db: DB, _: Manager, status_: Annotated[OrderStatus | None, Query(alias="status")] = None,
                customer_id: uuid.UUID | None = None, open_only: bool = False):
    return [svc.order_out(o) for o in svc.list_orders(db, status_, customer_id, open_only)]


@router.post("/orders", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(body: OrderCreate, db: DB, user: Manager):
    return svc.order_out(svc.create_order(db, body, user))


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: uuid.UUID, db: DB, _: Manager):
    return svc.order_out(svc.get_order(db, order_id))


@router.put("/orders/{order_id}", response_model=OrderOut)
def update_order(order_id: uuid.UUID, body: OrderUpdate, db: DB, user: Manager):
    return svc.order_out(svc.update_order(db, svc.get_order(db, order_id), body, user))


@router.post("/orders/{order_id}/deliver", response_model=SaleOut)
def deliver_order(order_id: uuid.UUID, body: DeliverIn, db: DB, user: Manager):
    _, sale = svc.deliver_order(db, svc.get_order(db, order_id), body, user)
    return svc.sale_out(sale)


@router.post("/orders/{order_id}/cancel", response_model=OrderOut)
def cancel_order(order_id: uuid.UUID, body: CancelIn, db: DB, user: Manager):
    return svc.order_out(svc.cancel_order(db, svc.get_order(db, order_id), body.reason, user))


# ---- debts ----

@router.get("/debts", response_model=list[DebtorOut])
def debts(db: DB, _: Manager):
    return svc.debts(db)
