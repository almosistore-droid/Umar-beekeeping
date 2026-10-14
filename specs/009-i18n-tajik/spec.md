# Feature Specification: Two languages — Русский and Тоҷикӣ

**Feature Branch**: `009-i18n-tajik` · **Created**: 2026-10-14 · **Status**: Ready for planning
**Input**: Owner (2026-10-14): «Нужен на двух языках» → Tajik; everything translated; language from Telegram,
switch in «Ещё», remembered.

## User Scenarios & Testing

### US1 Automatic language (P1)
A user whose Telegram is in Tajik (`language_code` starting with `tg`) sees the app in Tajik on the first
open; everyone else in Russian.

### US2 Switch (P1)
«Ещё → Забон / Язык»: Русский / Тоҷикӣ. The choice is remembered on the device and on the server
(users.language) and wins over Telegram's language.

### US3 Everything is translated (P1)
Screens, buttons, forms, hints, charts, server errors and validation messages, hive timeline, hive check,
dashboard/report labels, PDF/Excel/CSV exports, QR labels PDF, bot messages and captions.
Numbers and dates keep the same format; user data (names, notes) is never translated.
**Acceptance**: an automated test fails if any Russian UI string used in the app has no Tajik translation;
server errors come back in Tajik when the app is in Tajik.

## Requirements
- FR-001 Frontend `t(ru, ...args)` with the Russian text as the key; missing translation → Russian.
- FR-002 Requests carry `X-Lang: ru|tg`; the server translates its messages by template.
- FR-003 `users.language` (nullable: null = follow Telegram), `PUT /api/auth/me/language`.
- FR-004 Bot texts follow the user's saved language, else Telegram's.

Note: translations were written by the assistant and should be reviewed by a native speaker; the catalog
is one file per side so corrections are easy (`frontend/src/i18n/tg.json`, `backend/app/i18n/tg.json`).
