# Implementation Plan: Hive health records

**Branch**: `003-hive-health-records` | **Date**: 2026-10-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-hive-health-records/spec.md`

## Summary

Add inspections, a disease catalog with per-hive disease cases, treatments, feedings and reminder
tasks, plus a unified hive timeline. Records are written through services that keep the hive's
derived state (last/next inspection, family strength, SICK/QUARANTINE status) consistent and audit
every change. Frontend gets bottom-sheet forms launched from the hive card quick actions and a
timeline tab replacing the raw history list.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.6 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy 2 (sync), Alembic, Pydantic 2; React 18, TanStack Query 5

**Storage**: PostgreSQL 16 — 6 new tables (see data-model.md), new enum types, catalog seeded in the migration

**Testing**: pytest on PostgreSQL migrated by Alembic; Vitest + Testing Library

**Target Platform**: Telegram Mini App (iOS/Android WebView), Linux server in Docker

**Project Type**: web application (backend + frontend)

**Performance Goals**: timeline for a hive with 5 years of weekly records (~300 items) in one request

**Constraints**: mobile-first forms usable one-handed; Russian messages; no hard deletes

**Scale/Scope**: up to a few hundred hives per account

## Constitution Check

| Principle | How this plan complies |
|---|---|
| I. History is untouchable | No delete endpoints. Corrections via PUT write `audit_logs` with old/new values. Disease cases end with RESOLVED, reminders with DONE/CANCELLED. Timeline merges records + audit events. |
| II. Security by default | Every endpoint requires JWT; writes require `CAN_WRITE`, catalog edits `CAN_MANAGE`. Treatment `performed_by` and inspection `user_id` come from the token, never the body. |
| III. Relational data in PostgreSQL | All fields are typed columns with CHECK constraints (frames ≥ 0, brood+honey+pollen ≤ total, quantity > 0, resolved_at ≥ detected_at, next date ≥ date). One Alembic migration; `alembic check` clean. |
| IV. Mobile-first | Inspection form = chips/steppers, defaults pre-filled, one sticky Save button; forms open as bottom sheets from the hive card. |
| V. Tested, real | Service rules covered by API tests (status transitions, reminders, last-inspection logic, permissions); component tests for inspection form and timeline. Seed extended. |

Gate: PASS (no violations; Complexity Tracking not needed).

## Research decisions

- **Hive status from disease cases** — derived in `health_service.sync_hive_health_status()` after
  every case change: open CONFIRMED/TREATING cases → SICK or QUARANTINE (quarantine flag wins).
  Reverting only happens from SICK/QUARANTINE to ACTIVE, so manual statuses like WEAK are kept.
  Alternative "compute status on read" rejected: status is filtered/indexed and shown in lists.
- **Last inspection** — `hives.last_inspection_at = max(inspected_at)` recomputed after create/edit
  (cheap aggregate on an indexed column); avoids drift when an older inspection is entered later.
- **Reminders** — a generic `tasks` table (spec section 4 lists `tasks`) with `kind`
  (TREATMENT / FEEDING / INSPECTION / OTHER), `source_type`/`source_id`. Stage 8 will deliver them
  via the bot. Closing rule implemented in the service creating the new record.
- **Timeline** — server-side merge (one endpoint) so the client does not join 5 lists; items are a
  discriminated shape `{kind, at, title, details[], author, ref}`; audit events of kinds already
  represented by records (inspection/treatment created) are skipped to avoid duplicates.
- **Enumerations** — Postgres enums for statuses/levels; queen condition and food level as enums
  with Russian labels in the frontend.

## Project Structure

### Documentation (this feature)

```text
specs/003-hive-health-records/
├── spec.md
├── plan.md            # this file
├── data-model.md
├── contracts/api.md
├── quickstart.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code

```text
backend/app/
├── models/health.py            # Inspection, Disease, HiveDisease, Treatment, Feeding, Task
├── models/enums.py             # + new enums
├── schemas/health.py
├── repositories/health_repository.py
├── services/inspection_service.py
├── services/health_service.py  # diseases, cases, treatments, feedings, tasks, status sync
├── services/timeline_service.py
├── routers/health.py           # /api/hives/{id}/inspections|diseases|treatments|feedings|timeline|tasks
├── routers/catalog.py          # /api/diseases, /api/tasks
└── alembic/versions/0003_*.py  # tables + seeded disease catalog
backend/tests/test_health.py

frontend/src/
├── api/resources.ts            # + healthApi
├── pages/HiveDetailsPage.tsx   # quick actions open sheets; Timeline tab; reminders card
├── components/health/InspectionForm.tsx, DiseaseForm.tsx, TreatmentForm.tsx, FeedingForm.tsx
├── components/health/Timeline.tsx
├── utils/labels.ts             # + labels for new enums
└── test/stage3.test.tsx
```

**Structure Decision**: existing web-app layout (backend/ + frontend/) and layering are kept.
