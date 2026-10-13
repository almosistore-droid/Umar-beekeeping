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

## Auth
- `POST /api/auth/telegram` validates `initData` (HMAC-SHA256, key = HMAC("WebAppData", bot_token)) in `app/auth/telegram.py`, then issues a JWT.
- Never trust a Telegram user id from the client. The role is loaded from DB on every request (`get_current_user`).
- Protect endpoints with `Depends(require_roles(*CAN_WRITE))` etc. from `app/auth/dependencies.py`.

## Frontend
- Mobile-first; cards and big buttons, no wide tables.
- Brand: Fayzi Umar (logo `frontend/public/logo.webp`). Palette tokens at the top of `src/styles.css` (`--pitch`, `--comb`, `--gold`, `--amber`, `--wax`…); the app keeps this dark palette in every Telegram theme and paints Telegram's header to match. Hexagon (`--hex`) is the brand motif: hive numbers, nav scanner button, icon cells. Titles use Forum, body Manrope (self-hosted via @fontsource). Icons: `src/components/Icon.tsx` (no emoji in UI).
- Data fetching via TanStack Query; HTTP via `src/api/client.ts` (token in memory only).
- Bottom nav: Главная / Ульи / Сканер / Матки / Отчёты / Ещё.

## Commands
- Backend tests: `cd backend && .venv/bin/pytest` (DB `beekeeping_test`, migrated with Alembic in conftest).
- Frontend: `cd frontend && npm test && npm run build`.
- After each stage report: what was done, files changed, how to verify, tests passed.
