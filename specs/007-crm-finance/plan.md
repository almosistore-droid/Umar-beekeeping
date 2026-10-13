# Implementation Plan: CRM

Constitution: nothing deleted (cancel / archive, audit) ✅ · roles enforced server-side (CAN_MANAGE) ✅ ·
PostgreSQL generated columns for line totals, migration 0006 ✅ · mobile cards, sheets, big buttons ✅ · tests ✅

## Structure
```
backend/app/models/crm.py            Customer, Expense, Sale, SaleItem, Payment, Order, OrderItem
backend/app/schemas/crm.py
backend/app/services/crm_service.py  customers, expenses, sales, payments, orders, debts, summary
backend/app/routers/crm.py           /api/crm/...
frontend/src/pages/crm/*             CrmHome, Sales, SaleDetails, Expenses, Orders, OrderDetails, Customers, CustomerDetails, Debts
frontend/src/components/crm/*        ItemsEditor, SaleForm, PaymentForm, ExpenseForm, OrderForm, CustomerForm
```

## Decisions
- Sales and orders have lines (`sale_items`, `order_items`) with generated `total`; sale total is the
  sum of its lines (computed in SQL), paid = sum of payments.
- Income is accrual (by sale date); «получено» (cash) is shown separately.
- Order delivery copies lines into a new sale; `sales.order_id` unique.
- Statuses forward-only, enforced in the service; cancellation keeps the row with reason.
- Honey stock = Σ harvests kg − Σ sold HONEY lines in KG (not cancelled).
