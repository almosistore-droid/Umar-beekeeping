# Tasks: QR codes, scanner and deep links

**Input**: `specs/005-qr-and-deep-links/` — tests required (constitution V).

## Phase 1–2: Setup & foundation
- [x] T001 Spec, plan, data model, contract (this folder)
- [x] T002 segno, reportlab, httpx runtime deps; DejaVu fonts bundled
- [x] T003 QrCode model, migration 0005 with backfill

## Phase 3: US1 Permanent QR (P1) 🎯
- [x] T004 qr_service: payload, deep link, parse, ensure, svg; create_hive creates the QR
- [x] T005 GET/POST /api/hives/{id}/qr
- [x] T006 [P] Tests: created with hive, payload stable through number/apiary/queen changes, deep link variants
- [x] T007 Frontend HiveQrCard + sheet on the hive card

## Phase 4: US2 Labels (P1)
- [x] T008 PDF labels, bot delivery, audit qr_printed
- [x] T009 [P] Tests: PDF label count, blanks, refusals, Telegram delivery mocked, roles
- [x] T010 Frontend QrLabelsPage (Ещё → QR-наклейки), print from the hive QR sheet

## Phase 5: US3/US4 Scanner and deep link (P1)
- [x] T011 /api/qr/resolve with all accepted formats
- [x] T012 [P] Tests for found / unknown / invalid / archived
- [x] T013 Frontend ScanPage (Telegram scanner + manual), OpenQrPage, start_param routing

## Phase 6: US5 Registration (P2)
- [x] T014 HiveCreate.id; conflict when taken; tests
- [x] T015 HiveFormPage `?qr=` banner

## Phase 7: Polish
- [x] T016 describeAudit qr_printed; component tests; docs (README, CLAUDE.md, TESTING.md, .env.example); full run; CI

## Phase 8: US6 Field flow after a scan (added 2026-10-13)
- [x] T017 hive_check_service + GET /api/hives/{id}/check; tests (verdicts, every issue, read-only, roles)
- [x] T018 HiveVisitPage (choice), HiveInspectPage (full screen, done actions), HiveCheckPage; scan → /visit
- [x] T019 InspectionForm: date buttons, queen condition, swarming Да/Нет; «Осмотры» tab by date
- [x] T020 Component tests; docs
