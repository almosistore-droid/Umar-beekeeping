# CLAUDE.md — notes for AI assistants working on this repo

Beekeeping management Telegram Mini App. Full product spec: `docs/requirements.md` (Russian). Project principles: `.specify/memory/constitution.md` — they override everything else here. Work is done in 10 stages (see README status table). Do not start a stage before the previous one passes its tests.

## Spec Kit workflow
New stage or large feature: `/speckit-specify` → `/speckit-clarify` (optional) → `/speckit-plan` → `/speckit-tasks` → `/speckit-analyze` (optional) → `/speckit-implement`. Specs live in `specs/NNN-name/`. Stages 1–2 were built before Spec Kit was added; their behaviour is documented below and in tests.

## Architecture rules
- Backend: FastAPI, **sync** SQLAlchemy 2 (psycopg 3), PostgreSQL only (never SQLite). Layers: `routers` (HTTP) → `services` (business rules, audit) → `repositories` (queries) → `models`.
- Every schema change goes through an **Alembic migration** in `backend/alembic/versions/` (`alembic revision --autogenerate -m ... --rev-id NNNN`, then review). `alembic check` must report no drift.
- UUID primary keys (`UUIDPrimaryKeyMixin`), `created_at/updated_at` (`TimestampMixin`). Constraint naming convention is in `models/base.py`.
- Never hard-delete historical data (hives, families, queens): change status and keep history.
- Store dates of birth, never ages. Compute derived values (age, total_value) in code/SQL.
- Error messages returned to users are in Russian (`detail`), validation errors use the shape `{detail, errors:[{field,message}]}`.

## Domain rules (stage 2)
- Hive UUID is permanent (QR target). Number is unique per apiary only among non-archived hives (partial unique index).
- Archived hive statuses: MERGED, SOLD, LOST. Selling/losing a hive ends its family and retires its queen.
- One ACTIVE family per hive and one queen per hive are enforced by partial unique indexes; services flush the old row before inserting the new one.
- Queen history = `queen_assignments` (installed_at/removed_at per hive). Queen age is computed in `app/utils/age.py`.
- Every write goes through a service that calls `audit_service.record(...)` with the changed fields only; `GET /api/hives/{id}/history` reads it.
- Hives carry `version`; PUT with a stale version returns 409.
- `app/utils/seed.py` creates demo data through the services; extend it in each stage.

## Domain rules (stage 3 — specs/003-hive-health-records)
- Inspections recompute hive state in `inspection_service._recompute_hive`: last/next inspection from the latest inspection (default +7 days, stored at 12:00 UTC), current family strength from it.
- Disease cases: SUSPECTED → CONFIRMED → TREATING → RESOLVED, never backwards; `health_service.sync_hive_health_status` sets SICK/QUARANTINE (quarantine diseases) while CONFIRMED/TREATING cases exist and returns to ACTIVE only from SICK/QUARANTINE.
- Disease catalog is seeded by migration 0003; tests keep it (conftest truncates everything except `diseases`).
- Next treatment/feeding dates create `tasks` (reminders); a new record of the same kind closes older open ones. Stage 8 will send them via the bot.
- `GET /api/hives/{id}/timeline` merges records with audit events; the frontend describes events with `describeAudit` in `src/utils/labels.ts`.
- Health records are written by CAN_WRITE (assistants included); the disease catalog by CAN_MANAGE.

## Domain rules (stage 4 — specs/004-harvest-and-colony-operations)
- `total_value` on honey_harvests/other_products is a PostgreSQL generated column (weight×price); never write it.
- Harvest number = next per (hive, calendar year), assigned under a row lock on the hive; `apiary_id` stores where the hive stood at harvest time.
- Colony operations live in `operations_service` and run in one transaction; stage 2 helpers `create_hive`, `replace_family`, `end_family` accept `commit=False` for that.
- Merge: non-target sources → MERGED (archived), families closed MERGED, queens not kept → REPLACED; target without a queen → QUEENLESS. Sources in `hive_merge_sources`.
- Split without a queen → new hive QUEENLESS. Wintering result DIED → `end_family(DEAD)`.
- Operations are shown in timelines through audit actions (moved, swarmed, swarm_settled, split, split_created, merged_into, merge_target, wintering_*), described in `describeAudit`.
- Chart colour for honey bars `#c08918` (validated in-band on the dark card surface); highlight uses `--gold`.

## Domain rules (stage 5 — specs/005-qr-and-deep-links)
- QR payload is `hive_<hive uuid>` (Telegram startapp, ≤64 chars), stored in `qr_codes` (one per hive, created in `create_hive`, backfilled by migration 0005). It never changes.
- QR content = `qr_service.deep_link(code)`: `t.me/<bot>/<short_name>?startapp=` or `t.me/<bot>?startapp=` (Main Mini App); without TELEGRAM_BOT_USERNAME it is the bare code and the UI warns before printing.
- `qr_service.parse` accepts t.me links, `startapp=`/`tgWebAppStartParam=`, `hive_<uuid>`, bare UUID, `/hives/<uuid>`; `/api/qr/resolve` returns `found | unknown | invalid` (200, not 404).
- Unknown QR → CAN_MANAGE may register a hive with that id (`HiveCreate.id`, frontend `/hives/new?qr=`).
- Labels PDF (`qr_labels.py`, reportlab, bundled DejaVu fonts in `app/assets/fonts`): 3×4 on A4. In Telegram the bot sends it to the requesting user's own chat (`telegram_bot.send_document`); prints are audited as `qr_printed` only after successful delivery.
- Frontend: `/scan` (Telegram `showScanQrPopup`, manual fallback), `/open?code=` resolver, start_param handled once in `AppLayout` via `takeStartParam()`, `/qr-labels`.
- Field flow: a found, non-archived hive opens `/hives/:id/visit` → «Осмотр» (`/hives/:id/inspect`, full-screen InspectionForm with `doneActions`) or «Проверка» (`/hives/:id/check`, read-only `GET /api/hives/{id}/check` from `hive_check_service`: verdict ok/attention/problem + issues). Past inspection dates are sent as noon UTC. Hive passport has an «Осмотры» tab (`InspectionList`).

## Domain rules (stage 6 — specs/006-dashboard-and-yearly-report)
- Read-only aggregation, no new tables. `GET /api/dashboard` (dashboard_service) feeds the home screen in one request; `GET /api/reports/yearly/{year}` (report_service); exports `GET …/export?format=pdf|xlsx|csv`, bot delivery `POST …/send?format=`.
- Hive lifecycle in reports comes from history: start = installation_date (or created_at), end = merge date (MERGED) or the audit entry that set SOLD/LOST. Year end = min(31 Dec, today); years 2000…current, otherwise 422.
- Exports in `report_export.py` share `summary()`; CSV is UTF-8 BOM with «;» and Russian number format; PDF reuses the DejaVu fonts.
- Frontend charts: `components/charts/ColumnChart` (columns, tap tooltip, table toggle) and `BarList` (horizontal, values as text). One hue `#c08918`, highlight `--gold`. File delivery: `components/files/DeliverButtons` (bot in Telegram, download in a browser).
- Money on the dashboard (`finance`) and in the report (`finance.visible`) is returned only to ADMIN/BEEKEEPER.

## Domain rules (stage 7 — specs/007-crm-finance)
- CRM (`/api/crm/*`, `crm_service`) is ADMIN/BEEKEEPER only (403 for others). Bottom nav shows «CRM» instead of «Матки» for them (`navItems(canManage)`); queens move to «Ещё».
- Sales and orders have lines with PostgreSQL generated `total`; sale total = Σ lines, paid = Σ payments, debt = total − paid. Overpayment refused; credit/partial sales need a customer.
- Nothing is deleted: customers archived; expenses/sales/orders cancelled with a reason (sale with payments cannot be cancelled; a sale from an order is cancelled via the order). Order status NEW → READY → DELIVERED (deliver creates the sale in one transaction) or CANCELLED.
- Income = sales by sale date; received = payments by date; profit = income − expenses. Honey stock = Σ harvest kg − Σ sold HONEY kg.
- Currency label: `CURRENCY` setting (default «смн»), `GET /api/crm/settings`. Frontend forms in `components/crm/forms.tsx`, pages in `pages/crm/`.

## Auth
- `POST /api/auth/telegram` validates `initData` (HMAC-SHA256, key = HMAC("WebAppData", bot_token)) in `app/auth/telegram.py`, then issues a JWT.
- Never trust a Telegram user id from the client. The role is loaded from DB on every request (`get_current_user`).
- Protect endpoints with `Depends(require_roles(*CAN_WRITE))` etc. from `app/auth/dependencies.py`.

## Frontend
- Mobile-first; cards and big buttons, no wide tables.
- Brand: Fayzi Umar (logo `frontend/public/logo.webp`). Palette tokens at the top of `src/styles.css` (`--pitch`, `--comb`, `--gold`, `--amber`, `--wax`…); the app keeps this dark palette in every Telegram theme and paints Telegram's header to match. Hexagon (`--hex`) is the brand motif: hive numbers, nav scanner button, icon cells. Titles use Forum, body Manrope (self-hosted via @fontsource). Icons: `src/components/Icon.tsx` (no emoji in UI).
- Data fetching via TanStack Query; HTTP via `src/api/client.ts` (token in memory only).
- Bottom nav: Главная / Ульи / Сканер / CRM (admin, beekeeper) or Матки (others) / Отчёты / Ещё.

## Commands
- Backend tests: `cd backend && .venv/bin/pytest` (DB `beekeeping_test`, migrated with Alembic in conftest).
- Frontend: `cd frontend && npm test && npm run build`.
- After each stage report: what was done, files changed, how to verify, tests passed.
