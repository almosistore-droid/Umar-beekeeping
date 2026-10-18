# Feature Specification: Queen rearing calendar

**Feature Branch**: `016-queen-rearing` · **Created**: 2026-10-18 · **Status**: Implemented
**Input**: owner (2026-10-18): «Календарь вывода маток».

## Batch
Grafting day (day 0, larvae 12–24 h), how many larvae were grafted, optional mother queen and cell-builder hive,
optional name (default «Партия N · dd.mm», N per year), notes. Statuses ACTIVE → DONE (finished) or CANCELLED (with a
reason, ADMIN/BEEKEEPER). Grafting date: not in the future, not older than 60 days. Nothing is deleted.

## Calendar (days after grafting)
| Day | Step | Count recorded |
| --- | --- | --- |
| 0 | Прививка личинок | — |
| 1 | Проверить приём личинок | accepted |
| 5 | Маточники запечатаны | sealed |
| 10 | Разнести маточники по нуклеусам | — |
| 12 | Выход маток | emerged |
| 19 | Облёт и спаривание | — |
| 26 | Проверить засев | mated (laying) |
Each future step is a reminder in `tasks` (kind OTHER, `source_type = rearing:<step>`, hive = cell builder), so the bot
sends it like other reminders. Counts never exceed the grafted number or the previous recorded step. Changing the
grafting day or the cell builder moves the open reminders; finishing or cancelling closes them. Steps already past
when a batch is entered get no reminder (shown as «пора»).

## Who
Everyone sees; ADMIN, BEEKEEPER, ASSISTANT create, edit, record steps and finish; cancel — ADMIN, BEEKEEPER.

## API / screens
`GET|POST /api/rearing`, `GET|PUT /api/rearing/{id}`, `POST …/steps/{key}/done {count}`, `POST …/finish`,
`POST …/cancel`. «Ещё → Вывод маток»: active batches (day, step now/next, counts), batch page with the step timeline.
