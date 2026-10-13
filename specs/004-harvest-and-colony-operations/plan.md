# Implementation Plan: Harvest and colony operations

**Branch**: `004-harvest-and-colony-operations` | **Date**: 2026-10-13 | **Spec**: [spec.md](./spec.md)

## Summary

Seven new tables (honey_harvests, other_products, swarms, hive_splits, hive_merges +
hive_merge_sources, hive_movements, winterings). Values (`total_value`) are PostgreSQL generated
columns so they can never disagree with weight × price. Colony operations are implemented in one
service (`operations_service`) reusing stage 2 primitives (`create hive`, `replace family`, queen
`_detach`/`assign`) so families, queens and audit stay consistent. Honey statistics are SQL
aggregates. The timeline gains seven new item kinds.

## Technical Context

Same stack as stage 3 (Python 3.12 / FastAPI / SQLAlchemy 2 / Alembic / PostgreSQL 16; React 18,
TanStack Query). Scale: hundreds of hives, tens of harvests per hive per year.

## Constitution Check

| Principle | Compliance |
|---|---|
| I. History | Merged hives → MERGED (archived), families closed MERGED, queens REPLACED; movements keep from/to; nothing deleted. Merge sources in an association table. All operations audited and shown in timelines of every hive involved. |
| II. Security | Harvests/products: CAN_WRITE. Structural operations (move, swarm settle, split, merge, wintering): CAN_MANAGE. Performer from token. |
| III. Relational | No JSON; association table for merge sources; generated columns for values; CHECKs for weight > 0, price ≥ 0, frames ≥ 0, quantity > 0, end ≥ start, from ≠ to; unique (hive, season) for wintering; unique (hive, year, number) for harvests. |
| IV. Mobile | «Мёд» quick action; operations behind one «Операции» card with 5 buttons opening bottom sheets. |
| V. Tests | API tests per acceptance scenario; component tests for honey form and stats page. |

Gate: PASS.

## Research decisions

- **Harvest number**: computed in the service as `max(number)+1` for (hive, year) under a row lock
  on the hive, protected by a unique constraint.
- **Honey statistics**: one endpoint `GET /api/honey/stats?year=` returning totals, monthly series
  and per-hive ranking; hive card gets `honey_year_kg` via `GET /api/hives/{id}/honey`.
- **Merge target**: existing hive (may be a source) or a new hive number in the target's apiary.
- **Wintering result DIED**: reuses `hive_service.end_family` with status DEAD.
- **Timeline**: honey, product, swarm, split (both sides), merge (both sides), movement, wintering
  start/end items built from the records.

## Source Code

```text
backend/app/models/operations.py          # 8 models
backend/app/schemas/operations.py
backend/app/services/honey_service.py     # harvests, products, stats
backend/app/services/operations_service.py# move, swarm, split, merge, wintering
backend/app/routers/operations.py
backend/alembic/versions/0004_*.py
backend/tests/test_operations.py
frontend/src/components/operations/*      # HoneyForm, MoveForm, SwarmForm, SplitForm, MergeForm, WinteringForm, ProductForm
frontend/src/pages/HoneyPage.tsx, ProductsPage.tsx
frontend/src/test/stage4.test.tsx
```
