# API contract — stage 4

W = ADMIN/BEEKEEPER/ASSISTANT, M = ADMIN/BEEKEEPER.

| Method | Path | Role | Notes |
|---|---|---|---|
| GET | /api/hives/{id}/honey | any | `{items, year_kg, year_value, all_time_kg}` |
| POST | /api/hives/{id}/honey | W | 201 → harvest (number auto) |
| PUT | /api/honey/{id} | W | correction, audited |
| GET | /api/honey/stats?year=&apiary_id= | any | `{month_kg, year_kg, season_kg, all_time_kg, year_value, avg_per_hive_kg, producing_hives, best_hive, by_month[12], by_hive[]}` |
| GET | /api/products?year= | any | list |
| POST | /api/products | W | |
| POST | /api/hives/{id}/move | M | `{to_apiary_id, movement_date?, reason?, new_hive_number?}` → hive |
| GET | /api/hives/{id}/movements | any | |
| POST | /api/hives/{id}/swarms | M | `{swarm_date?, swarm_count, captured, settle_into_hive_id? | new_hive_number?, queen_id?, actions?}` |
| POST | /api/hives/{id}/split | M | `{split_date?, new_hive_number? | target_hive_id?, queen_id?, strength?, notes?}` → `{source, new_hive}` |
| POST | /api/merges | M | `{source_hive_ids[≥2], target_hive_id? | new_hive_number?+apiary_id?, keep_queen_id?, merge_date?, notes?}` → target hive |
| GET | /api/hives/{id}/winterings | any | |
| POST | /api/hives/{id}/winterings | M | start |
| PUT | /api/winterings/{id}/finish | M | `{end_date?, spring_strength?, result}` |
