# Implementation Plan: QR codes, scanner and deep links

**Spec**: `spec.md` · **Constitution check**: history untouchable (QR never changes, prints are
audited) ✅ · security (codes carry only a UUID; resolution and registration require auth and role;
the bot sends PDFs only to the requesting user's own Telegram id) ✅ · PostgreSQL + Alembic ✅ ·
mobile-first (native Telegram scanner, PDF to chat) ✅ · tested ✅

## Technical context

- QR rendering: `segno` (pure Python, SVG for screen and matrix for PDF).
- PDF labels: `reportlab`, DejaVu Sans fonts bundled in `backend/app/assets/fonts` (Cyrillic, no
  system font dependency; reused by stage 6 reports).
- Telegram Bot API `sendDocument` via `httpx` (moved to runtime requirements).
- Frontend: `Telegram.WebApp.showScanQrPopup` (Bot API 6.4+); `initDataUnsafe.start_param`.

## Structure

```
backend/app/models/qr.py                 QrCode
backend/alembic/versions/…_0005_qr_codes.py   table + backfill for existing hives
backend/app/services/qr_service.py       payload, deep link, parse, ensure, resolve, svg
backend/app/services/qr_labels.py        PDF sheet
backend/app/services/telegram_bot.py     send_document
backend/app/routers/qr.py                /api/hives/{id}/qr, /api/qr/resolve, /api/qr/labels
backend/app/schemas/qr.py
frontend/src/pages/ScanPage.tsx, OpenQrPage.tsx, QrLabelsPage.tsx
frontend/src/components/qr/HiveQrCard.tsx
```

## Decisions

- **Payload `hive_<uuid>`** (40 chars, fits Telegram's 64-char start_param limit, `[A-Za-z0-9_-]`).
- **Deep link**: `t.me/<bot>/<short_name>?startapp=` when both are set; `t.me/<bot>?startapp=` (Main
  Mini App) when only the username is set; otherwise the bare payload (works with the in-app scanner
  only) and the UI warns before printing.
- **Resolve returns 200 with a status** instead of 404 so the UI can tell «unknown hive» (offer
  registration) from «not a hive QR».
- **Blank labels** are just fresh UUIDs; nothing is stored until a hive is registered with one.
- QR row is created inside `create_hive` (also covers split/swarm hives).
