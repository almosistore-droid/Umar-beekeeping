# Feature Specification: Warehouse (склад) with consumption norms

**Feature Branch**: `014-warehouse` · **Created**: 2026-10-17 · **Status**: Implemented
**Input**: owner (2026-10-17): «склад: мёд, рамки; на одну рамку сколько метров сима и сколько грамм вощины — в
настройках, система считает сама, и корм тоже». Answers: frames/foundation/wire, feed, medicines and own items;
frame preparation writes off from the stock; feedings write off by the norms; low stock → app and bot.

## Items
- System items (migration 0012, recreated by `stock_service.ensure_system`, cannot be archived, unit fixed):
  empty frames (pcs), frames with foundation (pcs), foundation (kg), wire (m), sugar, candy, protein feed (kg).
- Own items: any name (unique among active, case-insensitive), section FRAMES / FEED / MEDICINE / OTHER, unit
  pcs / kg / g / l / ml / m / pack, optional minimum. Archived instead of deleted.
- Honey is not an item: honey stock = Σ harvests − Σ sold honey (kg) − Σ honey fed to bees (kg/g). The CRM honey
  stock uses the same formula.

## Movements (balance = Σ not cancelled, never stored)
| Kind | Who | Sign | Notes |
| --- | --- | --- | --- |
| Receipt | ADMIN, BEEKEEPER, ASSISTANT | + | |
| Consumption | same | − | refused if more than the balance |
| Inventory | ADMIN, BEEKEEPER | ± | the real count; difference is recorded |
| Frame preparation | ADMIN, BEEKEEPER, ASSISTANT | wire −N×norm, foundation −N×norm/1000, empty −N, ready +N | norms copied into the batch |
| Feeding | automatic | − | syrup l/ml × sugar per litre, kg/g × sugar per kg; candy, protein, pollen substitute in kg/g |
| Treatment | automatic | − | medicine chosen in the treatment form with a quantity in the item's unit |
Automatic write-offs may go below zero (a record is never refused); such items are «low». Correcting a feeding /
treatment cancels the old write-off and makes a new one. Manual movements and whole frame batches are cancelled
with a reason (ADMIN, BEEKEEPER); nothing is deleted.

## Norms («Ещё → Нормы расхода», ADMIN/BEEKEEPER edit, everyone sees)
wire m per frame (3), foundation g per frame (110), sugar kg per l of syrup (0.63 = 1:1), sugar kg per kg of syrup (0.5).
Changing the norms does not recalculate past records.

## Warnings
Low = balance < 0 or below the minimum. Home screen banner (dashboard `stock_low`), warehouse screen, and a weekly
bot reminder «📦 На складе заканчивается: …» to ADMIN/BEEKEEPER (respects «Работа на пасеке»), button → `go_stock`.

## API
`GET /api/stock` (items, honey_kg, norms), `GET|PUT /api/stock/norms`, `POST /api/stock/items`, `GET|PUT
/api/stock/items/{id}`, `POST …/archive|restore`, `POST …/movements`, `POST /api/stock/movements/{id}/cancel`,
`GET|POST /api/stock/frame-preps`, `POST /api/stock/frame-preps/{id}/cancel`. Treatments accept
`stock_item_id` + `stock_quantity` and return them.
