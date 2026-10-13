# API contract — stage 3

All endpoints require `Authorization: Bearer <jwt>`. W = ADMIN/BEEKEEPER/ASSISTANT, M = ADMIN/BEEKEEPER.
Errors: `{detail}` (404/409/403) or `{detail, errors:[{field,message}]}` (422), Russian text.

| Method | Path | Role | Notes |
|---|---|---|---|
| GET | /api/hives/{id}/inspections | any | newest first |
| POST | /api/hives/{id}/inspections | W | 201 → `{inspection, hive, warnings[]}`; warnings e.g. `possible_queenless` |
| PUT | /api/inspections/{id} | W | correction, audited; recomputes hive state |
| GET | /api/diseases | any | catalog, `?include_inactive` |
| POST | /api/diseases | M | add catalog entry |
| GET | /api/hives/{id}/diseases | any | cases, open first |
| POST | /api/hives/{id}/diseases | W | open case → returns `{case, hive}` |
| PUT | /api/disease-cases/{id} | W | update/progress status → `{case, hive}` |
| GET | /api/hives/{id}/treatments | any | |
| POST | /api/hives/{id}/treatments | W | → `{treatment, hive}`; creates/closes reminders |
| PUT | /api/treatments/{id} | W | audited |
| GET | /api/hives/{id}/feedings | any | |
| POST | /api/hives/{id}/feedings | W | → `{feeding, hive}` |
| PUT | /api/feedings/{id} | W | audited |
| GET | /api/hives/{id}/timeline | any | merged items `{kind, at, title, details[], author, ref_id}` |
| GET | /api/tasks | any | `?status=OPEN&hive_id=&due_before=` |
| POST | /api/tasks/{id}/done | W | mark done |
| GET | /api/dashboard/attention | any | `{needs_inspection, open_tasks, overdue_tasks, sick}` |
