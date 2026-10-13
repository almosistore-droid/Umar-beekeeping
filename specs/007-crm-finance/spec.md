# Feature Specification: CRM — customers, orders, sales, debts, expenses, profit

**Feature Branch**: `007-crm-finance` · **Created**: 2026-10-13 · **Status**: Ready for planning
**Input**: Stage 7 of `docs/requirements.md` (section 20: expenses / sales categories, income, expenses,
profit computed automatically) extended by the owner on 2026-10-13: a separate «CRM» button with
customers, orders and debts; CRM visible to ADMIN and BEEKEEPER; «CRM» replaces «Матки» in the
bottom navigation for them (queens move to «Ещё»).

## User Scenarios & Testing

### US1 Expenses (P1)
Record an expense: date, category (ульи, рамки, вощина, корм, лекарства, оборудование, транспорт,
топливо, матки, семьи, ремонт, другое), amount, description, optionally apiary/hive. Correct it
(audited) or cancel it with a reason — never delete.
**Acceptance**: amount ≤ 0 or a future date is refused in Russian; cancelled expenses do not count.

### US2 Sales and payments (P1)
Record a sale: date, customer (optional), one or more lines (category мёд, воск, прополис, перга,
пыльца, матки, семьи, пчелопакеты, другое; quantity, unit, price) — the total is calculated. Payment
at the moment of sale: in full, partly, or on credit. Later payments are added to the sale.
**Acceptance**: line total = quantity × price (DB generated column); paid = Σ payments;
debt = total − paid; a payment larger than the debt is refused; a sale with payments cannot be
cancelled.

### US3 Customers (P1)
Customer card: name, phone (tap to call), city, notes; totals — bought, paid, debt; history of
orders, sales, payments. Archive instead of delete. Search by name or phone.

### US4 Debts (P1)
«Долги»: customers who owe money with the total and the unpaid sales; «Принять оплату» in one tap.

### US5 Orders (P2)
Order for a customer: lines like a sale, due date, notes. Status NEW → READY → DELIVERED, or
CANCELLED; never backwards. «Выдать» creates the sale from the order lines (with payment now, partly
or on credit) in one transaction and links it to the order.

### US6 Profit and summaries (P1)
CRM home for a period (month or year): income (sales), expenses, profit = income − expenses, money
received, outstanding debts, open orders, honey in stock (harvested − sold, kg); income and expenses
by month and by category. Home dashboard tiles and the yearly report (and its PDF/Excel/CSV)
get real income / expenses / profit — for ADMIN/BEEKEEPER only.

### Edge cases
- Assistants and viewers get 403 on every CRM endpoint and see no money on the dashboard/report.
- Currency label comes from settings (`CURRENCY`, default «смн»).
- Selling more honey than in stock is allowed (stock before the system existed) but warned.
