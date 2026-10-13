# Feature Specification: Dashboard, statistics and yearly report

**Feature Branch**: `006-dashboard-and-yearly-report`
**Created**: 2026-10-13 · **Status**: Ready for planning
**Input**: Stage 6 of `docs/requirements.md` — sections 21 DASHBOARD and 26 YEARLY REPORT,
API `GET /api/dashboard`, `GET /api/reports/yearly/{year}`.

## User Scenarios & Testing

### User Story 1 - Dashboard on the home screen (P1)
The home screen shows, from one request: hives total, queens in hives, strong / weak / sick /
queenless families, hives needing inspection, reminders, honey this year; and charts — honey by
month, honey by hive (top 10), family strength, diseases this year, queen ages. Income, expenses
and profit tiles are shown as «появится на этапе 7» until stage 7.

**Acceptance**: counts equal the hive list filters; archived hives are excluded; each chart is
one series with a tap tooltip and a table view; empty data shows a hint instead of an empty chart.

### User Story 2 - Yearly report (P1)
«Отчёты» → choose a year → the system builds:
- **Ульи**: at the start of the year, at the end of the year (today for the current year), new,
  lost, sold, merged, split (operations).
- **Матки**: in hives at the end of the year, new (first installed this year), replaced, average
  age (months) at the end of the year, best families by honey (top 5, with the queen).
- **Мёд**: total, average per producing hive, best and worst hive, by month, value of the
  harvest; other products by type.
- **Болезни**: cases detected, by disease (cases / resolved / open), treatments (count, most used
  medications), result: resolved vs still open.
- **Финансы**: production value from recorded prices; income/expenses/profit «этап 7».

**Acceptance**: numbers match hand-counted seed data (tests); a year with no data gives zeros, not
errors; a future year or before 2000 is refused in Russian.

### User Story 3 - Export (P1)
PDF, Excel (.xlsx) and CSV of the yearly report. Inside Telegram the bot sends the file to the
user's own chat; in a browser it is downloaded.

**Acceptance**: PDF opens and contains the Cyrillic headings; xlsx opens with sheets «Сводка»,
«Мёд по ульям», «Мёд по месяцам», «Болезни»; CSV is UTF-8 with BOM and «;» so Excel in a Russian
locale opens it directly.

## Requirements
- FR-001 `GET /api/dashboard?year=` (any role).
- FR-002 `GET /api/reports/yearly/{year}` (any role) + `available_years`.
- FR-003 `GET /api/reports/yearly/{year}/export?format=pdf|xlsx|csv` (download),
  `POST /api/reports/yearly/{year}/send?format=` (bot → own chat).
- FR-004 Archive dates come from history: merge date for merged hives, the audit entry that set
  SOLD/LOST for sold/lost ones. Nothing new is stored.
