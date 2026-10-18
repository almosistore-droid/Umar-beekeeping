# Stage 10: testing → security → optimisation → production

**Created**: 2026-10-18 · **Status**: Implemented (stage 9 not built yet — rerun these checks after it)
**Input**: requirements §38, §40 «Этап 10»; owner: copies of the databases to the owner's Telegram.

## Testing
- `tests/test_acceptance.py`: the ten scenarios of §38 (hive, queen, queen ↔ hive, inspection, honey, yearly honey,
  QR, Telegram deep link, Telegram authorisation incl. forged / foreign-bot / old initData, yearly report + exports).
- `tests/test_query_counts.py`: screens open with the same number of SQL queries for 3 and 15 hives (no N+1).
- `tests/test_no_secrets.py`: no bot tokens, private keys, filled secrets or .env files in git.
- `tests/test_security.py`, `tests/test_telegram_bot.py`. Coverage measured in CI, must stay ≥ 90 % (now 95 %).

## Security
- Dependencies without known vulnerabilities (FastAPI 0.142.2 / Starlette 1.7.0 / PyJWT 2.15.1, aiogram 3.31 /
  aiohttp 3.14.3, react-router 7.18.4); CI runs pip-audit (backend + bot) and `npm audit --omit=dev`.
  Remaining advisories are in the test runner only (vitest 2, not shipped).
- API description (/api/docs, /api/openapi.json) not published when ENVIRONMENT=production.
- JWT algorithm limited to HS256/384/512; unsigned / foreign-key / expired / wrong-type tokens refused (tests).
- Every /api route except the public ones answers 401 without a token (test walks all routes).
- Data answers `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`.
- Containers: no-new-privileges, capabilities dropped for backend, bot and owner panel, backend healthcheck,
  logs capped (10 MB × 3). `deploy/harden.sh`: ufw (SSH port, 80, 443), fail2ban (sshd), unattended upgrades,
  optional keys-only SSH (never without an installed key).

## Optimisation (measured on 300 hives, 6000 inspections, 900 harvests)
- Every screen < 150 ms; indexes added for timeline/report lookups (migration 0017).
- Frontend: less frequent screens load on first open and are warmed up in the background while online (offline
  keeps working); Tajik catalog loaded only for Tajik; React / router / query in separate long-cached files;
  first load 163 KB app + libraries (was one 648 KB file). gzip at nginx.

## Production
- `client.sh backup-setup` → `deploy/backup.env` (bot token, owner chat, generated password, chmod 600);
  `backup all --send`: pg_dump → gzip → AES-256-CBC (PBKDF2, 200k iterations, password via environment) →
  Bot API sendDocument (≤ 49 MB); local copies 30 days. `decrypt`, `restore SLUG FILE` (typed confirmation,
  safety copy first, schema replaced, migrations on start).
- `check [--alert]`: app health inside each backend, certificate days, disk ≥ 85 % → owner's Telegram, once per 6 h
  per problem set. `cron`: backups 02:30, renew 03:00, check every 15 min.
- `build` keeps the running images as `:previous` and tags `:<git sha>`; `update` backs up first; `rollback`.
