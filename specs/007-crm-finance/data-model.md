# Data model — stage 7 (migration 0006)

- **customers**: name, phone, city, notes, is_archived, created_by
- **expenses**: expense_date, category (expense_category), amount > 0, description, apiary_id?, hive_id?,
  cancelled_at?, cancel_reason, created_by
- **sales**: sale_date, customer_id?, order_id? (unique), notes, cancelled_at?, cancel_reason, created_by
- **sale_items**: sale_id, category (sale_category), quantity > 0, unit (feed_unit), price_per_unit ≥ 0,
  total GENERATED (quantity × price_per_unit)
- **payments**: sale_id, paid_at, amount > 0, method (payment_method: CASH / CARD / TRANSFER), notes, created_by
- **orders**: customer_id, order_date, due_date?, status (order_status: NEW / READY / DELIVERED / CANCELLED),
  notes, cancel_reason, created_by
- **order_items**: order_id, category, quantity, unit, price_per_unit, total GENERATED
