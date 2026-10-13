---
description: "Tasks for stage 3 — hive health records"
---

# Tasks: Hive health records

**Input**: `specs/003-hive-health-records/` (spec, plan, data-model, contracts)

**Tests**: required by the constitution (principle V) — included per story.

## Phase 1: Setup

- [x] T001 Create spec folder, plan, data model, contract, quickstart

## Phase 2: Foundational

- [x] T002 Add enums (queen_condition, food_level, inspection_health, disease_severity, disease_case_status, feed_type, feed_unit, task_kind, task_status) in backend/app/models/enums.py
- [x] T003 Models Inspection, Disease, HiveDisease, Treatment, Feeding, Task in backend/app/models/health.py; register in models/__init__.py
- [x] T004 Alembic migration 0003 with tables, CHECK constraints and seeded disease catalog
- [x] T005 Pydantic schemas with Russian validation messages in backend/app/schemas/health.py
- [x] T006 Shared guards (hive writable & has family), task helpers in backend/app/services/health_service.py

## Phase 3: US1 Inspections (P1) 🎯 MVP

- [x] T007 [US1] inspection_service: create/update, recompute last/next inspection, sync family strength, queenless warning, audit
- [x] T008 [US1] Routes GET/POST /api/hives/{id}/inspections, PUT /api/inspections/{id}
- [x] T009 [P] [US1] Tests: create, validation (frames, future date), archived/empty hive, older inspection does not move dates, correction audited, viewer forbidden
- [x] T010 [US1] Frontend InspectionForm (bottom sheet) + quick action «Осмотр» + warnings

## Phase 4: US2 Disease cases (P2)

- [x] T011 [US2] Catalog routes GET/POST /api/diseases
- [x] T012 [US2] Cases create/update with transition rules and hive status sync (SICK/QUARANTINE/ACTIVE)
- [x] T013 [P] [US2] Tests: confirmed → SICK, AFB → QUARANTINE, resolve last → ACTIVE, two cases, suspected no change, invalid transitions
- [x] T014 [US2] Frontend DiseaseForm + open cases card with «Вылечено»

## Phase 5: US3 Treatments (P2)

- [x] T015 [US3] Treatments create/update; case → TREATING; reminders create/close
- [x] T016 [P] [US3] Tests: link case, other hive's case refused, reminder created, closed by next treatment, next date before date refused
- [x] T017 [US3] Frontend TreatmentForm + reminders card on hive

## Phase 6: US4 Feedings (P3)

- [x] T018 [US4] Feedings create/update + feeding reminders
- [x] T019 [P] [US4] Tests: quantity > 0, reminder
- [x] T020 [US4] Frontend FeedingForm

## Phase 7: US5 Timeline (P2) + attention

- [x] T021 [US5] timeline_service merging records and audit events; GET /api/hives/{id}/timeline
- [x] T022 [US5] GET /api/tasks, POST /api/tasks/{id}/done, GET /api/dashboard/attention
- [x] T023 [P] [US5] Tests: order and summaries, tasks list/done, attention counts
- [x] T024 [US5] Frontend Timeline tab; home tile «Требуют осмотра» and reminders

## Phase 8: Polish

- [x] T025 Extend seed with inspections, a case, treatments, feedings
- [x] T026 Frontend component tests (inspection form validation message, timeline rendering)
- [x] T027 Update README status, CLAUDE.md domain rules, TESTING.md checklist
- [x] T028 Full test run, `alembic check`, build, screenshots, CI green
