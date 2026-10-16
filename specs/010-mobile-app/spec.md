# Feature Specification: App on the phone (iPhone and Android) outside Telegram

**Feature Branch**: `010-mobile-app` · **Created**: 2026-10-16 · **Status**: Ready for planning
**Input**: Owner (2026-10-16): «создадим отдельные приложения в iPhone и Android» → an icon on the home
screen installed from the site (PWA), no App Store / Google Play for now; before stage 8.

## User Scenarios & Testing

### US1 Install (P1)
On the app's HTTPS address in Safari (iPhone) or Chrome (Android) the user adds the app to the home screen
(Android: «Установить» button; iPhone: hint «Поделиться → На экран «Домой»»). It opens full-screen with the
Fayzi Umar icon and name, in the same dark design.

### US2 Login with Telegram, no password (P1)
Outside Telegram the app shows «Войти через Telegram». Tapping it opens the bot; the bot asks
«Войти в приложение Fayzi Umar?» with «Войти» / «Отмена». After «Войти» the user returns to the app and is
logged in with the same account, role and data as in the Mini App. Next launches open straight away
(device stays logged in) until «Выйти» or the admin blocks the user.
**Acceptance**: a code is one-time, expires after 5 minutes, only the device that requested it can collect
the session; a blocked user cannot log in or continue on a logged-in device; role is read from the DB on
every request as before.

### US3 Scan QR with the phone camera (P1)
«Сканер» outside Telegram opens the camera in the app and opens the hive passport after reading its QR code
(same codes, same resolver). Without a camera — manual input as before.

### US4 Everything else works the same (P1)
All screens, both languages, reports: download in the browser or send to the user's Telegram chat.

## Requirements
- FR-001 PWA: web manifest (name, icons 192/512 + maskable, standalone, dark colours), service worker that
  caches only the static app (never /api), iOS meta tags, safe-area paddings.
- FR-002 `POST /api/auth/login-codes` → code (in the bot deep link `t.me/<bot>?start=login_<code>`) and a
  poll secret kept by the requesting device; `POST /api/auth/login-codes/poll` → pending / denied / expired /
  session; bot-only `…/confirm` and `…/deny`, authenticated by HMAC of the bot token (header X-Bot-Auth).
- FR-003 Device session: random token stored hashed in `device_sessions`; `POST /api/auth/device` exchanges
  it for the usual JWT; expires after 180 days without use; `POST /api/auth/logout` revokes it.
- FR-004 Camera scanner: BarcodeDetector where available, otherwise jsQR on video frames.
- FR-005 Dev: the bot runs in the `telegram` profile and takes the current tunnel address from the tunnel.

Out of scope now: App Store / Google Play packages (the same PWA can be wrapped later), web push (stage 8
sends notifications through the bot, which reaches PWA users too), offline data entry.
