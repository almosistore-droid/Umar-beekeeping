# Feature Specification: Login and password (people without Telegram)

**Feature Branch**: `011-password-login` · **Created**: 2026-10-16 · **Status**: Implemented
**Input**: Owner (2026-10-16): «Без Телеграм можем отдельную программу» → login and password made by the admin;
the Telegram Mini App stays as an option.

## User Scenarios & Testing
- US1 (P1) The admin adds a person «Логин и пароль»: name, login, role → gets a temporary password once and
  sends it (share sheet). Users without Telegram are full users (roles, audit, all screens).
- US2 (P1) The person opens the app (browser / home-screen icon / Telegram), enters login and password, must
  replace the temporary password before anything else (also enforced by the server), then stays logged in on
  that phone (device session, as in 010).
- US3 (P1) The admin can give a Telegram user a login too (one account, two ways in) and issue a new temporary
  password; this logs the person out on every phone.
- US4 (P2) «Ещё → Сменить пароль».

## Requirements
- FR-001 users.telegram_id nullable; login (unique, lowercase), password_hash (scrypt), must_change_password,
  failed_logins, locked_until; CHECK telegram_id or login present.
- FR-002 `POST /api/auth/password` → JWT + device token; same answer for unknown login and wrong password;
  5 failures → 15-minute lock; blocked user → 403 only after the right password.
- FR-003 `PUT /api/auth/me/password` (current password required, ≥8 chars, ≠ login).
- FR-004 `POST /api/admin/accounts`, `POST /api/admin/users/{id}/password` (ADMIN only, not for oneself).
- FR-005 Bot delivery of files needs Telegram: without it the app offers only «Скачать».
- Audit: account_created, password_reset, password_changed, login_locked, device_login {method: password}.
