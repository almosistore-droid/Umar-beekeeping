# Data model — stage 5

## qr_codes

| column | type | notes |
|---|---|---|
| id | uuid PK | |
| hive_id | uuid FK hives, NOT NULL, UNIQUE | RESTRICT on delete (hives are never deleted) |
| code | varchar(64) NOT NULL UNIQUE | `hive_<hive uuid>` — the startapp payload, never changes |
| print_count | integer NOT NULL default 0, CHECK ≥ 0 | |
| last_printed_at | timestamptz | |
| created_by_id | uuid FK users, SET NULL | |
| created_at / updated_at | timestamptz | |

Migration 0005 backfills a row for every existing hive.

`hives.id` may be supplied on creation (registration of a pre-printed label).
