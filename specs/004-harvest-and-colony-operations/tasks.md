# Tasks: Harvest and colony operations

**Input**: `specs/004-harvest-and-colony-operations/` — tests required (constitution V).

## Phase 1–2: Setup & foundation
- [x] T001 Spec, plan, data model, contract (this folder)
- [x] T002 Enums ProductType, WinteringResult; models in backend/app/models/operations.py; migration 0004 with generated value columns and constraints
- [x] T003 Schemas with Russian validation in backend/app/schemas/operations.py

## Phase 3: US1 Honey (P1) 🎯
- [x] T004 honey_service: create/update harvest (auto number, apiary at harvest time), hive honey summary, stats
- [x] T005 Routes /api/hives/{id}/honey, /api/honey/{id}, /api/honey/stats
- [x] T006 [P] Tests: value computed, numbering per year, validation, stats correctness
- [x] T007 Frontend HoneyForm (quick action «Мёд»), honey on hive card, HoneyPage

## Phase 4: US2 Movement (P2)
- [x] T008 operations_service.move_hive with number conflict handling; routes
- [x] T009 [P] Tests: move, conflict, new number, same apiary refused
- [x] T010 Frontend MoveForm

## Phase 5: US3 Swarm / split / merge (P2)
- [x] T011 swarm (settle into empty or new hive), split, merge services + routes
- [x] T012 [P] Tests for each acceptance scenario incl. queen handling and refusals
- [x] T013 Frontend SwarmForm, SplitForm, MergeForm in «Операции» card

## Phase 6: US4 Wintering (P3)
- [x] T014 start/finish wintering; DIED closes family
- [x] T015 [P] Tests
- [x] T016 Frontend WinteringForm

## Phase 7: US5 Products (P3)
- [x] T017 Products routes + tests + ProductsPage

## Phase 8: Timeline & polish
- [x] T018 Timeline kinds for all stage 4 records (both sides for links)
- [x] T019 Seed: harvests over two seasons, a move, a split, a wintering, products
- [x] T020 Component tests; docs (README, CLAUDE.md, TESTING.md); full run; CI
