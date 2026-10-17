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
- «Today» is the apiary's calendar day: `schemas.common.today()` / `local_date(ts)` in `settings.timezone` (TIMEZONE, default Asia/Dushanbe), never `date.today()` or the UTC date. Dates stored as noon-UTC timestamps (next inspection) are read back with `stored_day()`. Tests use `app_today()` too.
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
- Next treatment/feeding dates create `tasks` (reminders); a new record of the same kind closes older open ones. Stage 8 sends them via the bot.
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

## Admin panel (specs/008-admin-panel) — ADMIN only
- `/api/admin/overview` (system, users by role, counts per section), `/api/admin/invites` (create / list / revoke), `/api/admin/audit` (all audit_logs, filters user_id / entity_type, offset paging — not timestamp cursors: one transaction shares a timestamp).
- Invitations (`user_invites`): by Telegram ID or lowercase username, 30 days, one PENDING per ID/username (partial unique indexes). `auth_service.upsert_telegram_user` claims one on a user's FIRST login (ID first, then username-only invites); ADMIN_TELEGRAM_IDS still wins. An ID listed in ADMIN_TELEGRAM_IDS is promoted to ADMIN on every login (audit `role_from_config`), even if the person logged in before. Inviting someone who already uses the app changes their role at once. `users.last_seen_at` is set on every login.
- Frontend: «Ещё → Админ-панель» (`pages/admin/AdminPage`), `/users` (access + invite sheet with Telegram share), `/admin/log` (`describeLogEntry`, `logDetail`).

## Languages (specs/009-i18n-tajik) — Russian + Tajik
- Russian text is the key. Frontend: every user-visible string goes through `tr("русский текст {0}", arg)` from `src/i18n`; translations in `src/i18n/tg.json`. `src/test/i18n.test.ts` fails on Cyrillic outside `tr()` (mark deliberate exceptions `// i18n-ignore`) and on missing/mismatched translations. Language is fixed per page load (localStorage `fayzi-umar.lang`, else Telegram `language_code`, else the server's `users.language`); switching reloads.
- Every request sends `X-Lang`. Backend: the `language` middleware sets `app.i18n.current_lang` and translates JSON responses (`detail`, errors, labels) via the template catalog `app/i18n/tg.json` (+ `tg_data.json` for seeded data such as disease names). User data is never translated. Files (PDF/XLSX/CSV, QR labels, bot captions) are translated explicitly with `L(text)`.
- New backend strings: run `python -m app.i18n.extract` — it lists strings missing from the catalog; `tests/test_i18n.py` enforces it. `users.language` (ru/tg) is saved by `PUT /api/auth/me/language`. Tajik letters need the Onest fallback font (Manrope lacks them).

## App on the phone (specs/010-mobile-app) — PWA outside Telegram
- PWA: `public/manifest.webmanifest`, icons `icon-192/512`, `icon-maskable-512`, `public/sw.js` (caches the static app only, never /api; HTML network-first), registered in production by `services/pwa.ts` (also install prompt / iOS hint, `components/auth/InstallHint`).
- Login outside Telegram (`components/auth/PhoneLogin`): `POST /api/auth/login-codes` → `tg://resolve?domain=<bot>&start=login_<code>`; the bot (`bot/handlers/login.py`) asks «Войти / Отмена» and calls `…/confirm` or `…/deny` with header `X-Bot-Auth` = HMAC(bot token, label) (`app/auth/bot_signature.py` = `bot/signing.py`, a test keeps them equal); the app polls `…/poll` with its poll secret. Codes: one-time, 5 min (`login_code_ttl_seconds`). `device_auth_service`.
- Device session: random token stored hashed in `device_sessions`, kept in localStorage `fayzi-umar.device` (the JWT stays in memory); `POST /api/auth/device` → JWT (blocked → 403, revoked/idle 180 days → 401), `POST /api/auth/logout`. `useAuth` state `signed-out` shows PhoneLogin; `onDevice` enables «Выйти». Audit action `device_login`.
- Scanner outside Telegram: `components/qr/CameraScanner` (BarcodeDetector, else lazy-loaded jsQR).
- Dev: the `telegram` profile runs the bot too; the tunnel writes its address to the shared volume (`URL_FILE`), the bot reads it (`WEBAPP_URL_FILE`, `SET_MENU_BUTTON=0`).

## Login and password (specs/011-password-login) — people without Telegram
- `users.telegram_id` is nullable; `login` (unique, lowercase), `password_hash` (scrypt, `app/auth/passwords.py`), `must_change_password`, `failed_logins`/`locked_until` (5 failures → 15 min). CHECK: telegram_id or login.
- `password_service`: `POST /api/auth/password` (same «Неверный логин или пароль» for unknown login / wrong password; blocked → 403 only after the right password) issues JWT + device token like the bot login; `PUT /api/auth/me/password`; admin `POST /api/admin/accounts`, `POST /api/admin/users/{id}/password` (temporary password returned once, revokes the person's device sessions).
- `get_current_user` returns 403 «Сначала смените временный пароль» except `PASSWORD_CHANGE_PATHS` while `must_change_password`; the frontend shows `ForcedPasswordChange` (`components/auth/PasswordForms`).
- Never assume `user.telegram_id` exists: bot delivery (`telegram_bot.send_document`) refuses without it; `DeliverButtons` hides «Отправить в чат».

## Stage 8 — Telegram reminders (specs/012-telegram-reminders)
- `notification_service.collect()` builds `Note`s (key, category field|crm, Russian lines, button + start param) from open tasks, hives' next inspection, old queens (≥24 months), QUEENLESS hives (weekly key), wintering prep/check (seasonal, yearly key), CRM debts (weekly key) and due orders; 30-day lookback, one more reminder after 3 days overdue.
- `dispatch()` (7:00–21:00 apiary time) claims (user, key) in `notification_log` with INSERT … ON CONFLICT DO NOTHING before sending; TelegramBlocked → FAILED (kept), TelegramUnavailable → row deleted (retried). Recipients: active users with telegram_id, ADMIN/BEEKEEPER all, ASSISTANT field only, VIEWER none; `users.notify_field` / `notify_crm`.
- Text per line through `translate(line, lang)`; buttons are t.me deep links (`hive_<uuid>` or `go_tasks|go_hives|go_debts|go_orders`, mapped by `START_SCREENS` in `AppLayout`).
- The bot (`bot/reminders.py`) calls `POST /api/notifications/dispatch` (X-Bot-Auth) every NOTIFY_EVERY_SECONDS (300). Settings/test: `/api/notifications/settings`, `/api/notifications/test`; UI card in «Ещё». Tests patch `ns._wintering` (seasonal).

## Subscription clients (specs/013-subscription-clients)
- One installation per client (own DB, domain, bot, `clients/<slug>.env`), same images; brand = runtime settings
  `BRAND_NAME/SUBTITLE/COLOR/LOGO`. Never hardcode «Fayzi Umar» or `/logo.webp`: backend `get_settings().brand_name`,
  frontend `useBranding()` / `getBranding()` (`src/services/branding.ts`, loaded in `main.tsx` before render).
- Public `/api/branding` (+ logo, icons, manifest via Pillow in `branding_service`). Brand colour → CSS vars `--gold`,
  `--gold-light`, `--gold-deep`, `--gold-rgb` (use `rgba(var(--gold-rgb), a)`, not literal colours).
- `SUBSCRIPTION_UNTIL` passed → middleware returns 402 for `/api/*` except health/branding; frontend
  `SubscriptionBlocked` (also on any 402 via `setPaymentRequiredHandler`), admin `SubscriptionWarning` ≤ 7 days.
- Deploy: `deploy/client.sh` + `deploy/client.yml` (no ports, aliases `<slug>-backend|frontend` on network
  `bee-edge`) + `deploy/edge` (nginx, generated `sites/<slug>.conf`). `COMPOSE_PROJECT` in a client env keeps an
  old project's volumes (`adopt`). Tests: `backend/tests/test_deploy_client.py` (fake docker/certbot).

## Auth
- `POST /api/auth/telegram` validates `initData` (HMAC-SHA256, key = HMAC("WebAppData", bot_token)) in `app/auth/telegram.py`, then issues a JWT.
- Never trust a Telegram user id from the client (the bot passes it only for login confirmation, signed). The role is loaded from DB on every request (`get_current_user`).
- Protect endpoints with `Depends(require_roles(*CAN_WRITE))` etc. from `app/auth/dependencies.py`.

## Frontend
- Mobile-first; cards and big buttons, no wide tables.
- Brand: per installation (default Fayzi Umar, logo `backend/app/assets/brand/logo.png`), see «Subscription clients». Palette tokens at the top of `src/styles.css` (`--pitch`, `--comb`, `--gold`, `--amber`, `--wax`…); the app keeps this dark palette in every Telegram theme and paints Telegram's header to match. Hexagon (`--hex`) is the brand motif: hive numbers, nav scanner button, icon cells. Titles use Forum, body Manrope (self-hosted via @fontsource). Icons: `src/components/Icon.tsx` (no emoji in UI).
- Data fetching via TanStack Query; HTTP via `src/api/client.ts` (token in memory only).
- Bottom nav: Главная / Ульи / Сканер / CRM (admin, beekeeper) or Матки (others) / Отчёты / Ещё.

## Dev tunnel (docker-compose.dev.yml, profile `telegram`)
- `tunnel/tunnel.py` (stdlib only) supervises a Cloudflare quick tunnel: sets each new address on the bot menu button via `setChatMenuButton` (real TELEGRAM_BOT_TOKEN from .env), health-checks every 30 s and starts a new tunnel after 4 failures. Image: python:3.12-slim + static cloudflared copied from the official image. Tests: `backend/tests/test_dev_tunnel.py`.

## Commands
- Backend tests: `cd backend && .venv/bin/pytest` (DB `beekeeping_test`, migrated with Alembic in conftest).
- Frontend: `cd frontend && npm test && npm run build`.
- After each stage report: what was done, files changed, how to verify, tests passed.
