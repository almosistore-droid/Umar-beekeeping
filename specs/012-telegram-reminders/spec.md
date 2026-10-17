# Feature Specification: Stage 8 — Telegram reminders

**Feature Branch**: `012-telegram-reminders` · **Created**: 2026-10-17 · **Status**: Implemented
**Input**: requirements §27 + owner's answers (2026-10-17): each reminder as its own message; inspections,
treatments/feedings, queens and wintering, CRM debts and orders; recipients by role, each can turn them off.

## What is sent (one message each, a button opens the hive or the screen)
| Reminder | When | Again |
| --- | --- | --- |
| Task (treatment, feeding, other) | on its due day (or the first run after it, up to 30 days back) | once more after 3 days |
| Inspection | the hive's next inspection day; overdue text = §27 example | once more after 3 days |
| Old queen (≥ 24 months) | once per queen | — |
| Hive without a queen | weekly while QUEENLESS | weekly |
| Wintering preparation | once a year, 15 Sep–Nov (families / weak families) | — |
| Wintering results | once a year, 20 Mar–Apr | — |
| Customer debt (CRM) | weekly while the debt remains | weekly |
| Order due (CRM) | on its due day (or overdue) | — |

## Rules
- Recipients: ADMIN and BEEKEEPER — everything; ASSISTANT — apiary work; VIEWER — nothing; only active users with
  Telegram. «Ещё → Напоминания в Telegram»: two switches (apiary work, CRM) and a test message.
- Sent only 7:00–21:00 apiary time; each (person, reminder key) is claimed in `notification_log` before sending, so
  nothing goes twice; a blocked bot is recorded as FAILED and not retried; Telegram errors are retried next run.
- Text in the person's language (ru/tg), translated line by line through the backend catalog.
- The bot calls `POST /api/notifications/dispatch` (signed like the login confirmation) every 5 minutes.
- People without Telegram see reminders in «Ещё → Напоминания» in the app (no push in this stage).
