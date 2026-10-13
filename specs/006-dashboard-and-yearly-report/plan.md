# Implementation Plan: Dashboard and yearly report

Constitution: read-only aggregation over existing history ✅ · PostgreSQL queries, no new tables ✅ ·
mobile-first cards and bars, files via the bot in Telegram ✅ · tested against seeded scenarios ✅

## Structure
```
backend/app/services/dashboard_service.py   tiles + chart series
backend/app/services/report_service.py      yearly report (hive lifecycle from history)
backend/app/services/report_export.py       PDF (reportlab), XLSX (openpyxl), CSV
backend/app/routers/reports.py              /api/dashboard, /api/reports/yearly/...
frontend/src/components/charts/             BarChart (vertical), HBarList (horizontal), shared tooltip/table
frontend/src/pages/HomePage.tsx, ReportsPage.tsx
```

## Decisions
- One hue for every chart (`#c08918`, highlight `--gold`) — all are single-series magnitude.
- Hive existence on a date: start = installation_date (or created_at), end = archive date
  from history. Year end = min(31 Dec, today).
- Queen age average in whole months at year end; queens without a birth date are skipped and counted.
- Export file generation is pure (bytes); delivery reuses `telegram_bot.send_document`.
- New dependency: `openpyxl`.
