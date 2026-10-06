# CLAUDE.md — notes for AI assistants working on this repo

Beekeeping management Telegram Mini App. Full product spec lives with the project owner; work is done in 10 stages (see README status table). Do not start a stage before the previous one passes its tests.

## Architecture rules
- Backend: FastAPI, **sync** SQLAlchemy 2 (psycopg 3), PostgreSQL only (never SQLite). Layers: `routers` (HTTP) → `services` (business rules, audit) → `repositories` (queries) → `models`.
- Every schema change goes through an **Alembic migration** in `backend/alembic/versions/` (`alembic revision --autogenerate -m ... --rev-id NNNN`, then review). `alembic check` must report no drift.
- UUID primary keys (`UUIDPrimaryKeyMixin`), `created_at/updated_at` (`TimestampMixin`). Constraint naming convention is in `models/base.py`.
- Never hard-delete historical data (hives, families, queens): change status and keep history.
- Store dates of birth, never ages. Compute derived values (age, total_value) in code/SQL.
- Error messages returned to users are in Russian (`detail`), validation errors use the shape `{detail, errors:[{field,message}]}`.

## Auth
- `POST /api/auth/telegram` validates `initData` (HMAC-SHA256, key = HMAC("WebAppData", bot_token)) in `app/auth/telegram.py`, then issues a JWT.
- Never trust a Telegram user id from the client. The role is loaded from DB on every request (`get_current_user`).
- Protect endpoints with `Depends(require_roles(*CAN_WRITE))` etc. from `app/auth/dependencies.py`.

## Frontend
- Mobile-first, Telegram theme variables (`--tg-*`) in `src/styles.css`; cards and big buttons, no wide tables.
- Data fetching via TanStack Query; HTTP via `src/api/client.ts` (token in memory only).
- Bottom nav: Главная / Ульи / Сканер / Матки / Отчёты / Ещё.

## Commands
- Backend tests: `cd backend && .venv/bin/pytest` (DB `beekeeping_test`, migrated with Alembic in conftest).
- Frontend: `cd frontend && npm test && npm run build`.
- After each stage report: what was done, files changed, how to verify, tests passed.
