# Data model — stage 3

All tables: UUID `id`, `created_at`, `updated_at` (except where noted). No deletes.

## hive_inspections
| column | type | rules |
|---|---|---|
| hive_id | FK hives | required, indexed with inspected_at |
| user_id | FK users | author, from token |
| inspected_at | timestamptz | ≤ now + 1 day |
| strength | family_strength | required |
| frames_total, brood_frames, honey_frames, pollen_frames | smallint | ≥ 0; brood+honey+pollen ≤ total; total ≤ 60 |
| queen_present | bool null | seen / not seen / not checked |
| queen_condition | queen_condition (GOOD, NORMAL, POOR, NOT_SEEN) null | |
| egg_laying | bool null | eggs seen |
| queen_cells | smallint | ≥ 0, default 0 |
| swarming_signs | bool | default false |
| food_level | food_level (CRITICAL, LOW, NORMAL, ABUNDANT) null | |
| aggressiveness | smallint null | 1–5 |
| health_status | inspection_health (HEALTHY, SUSPICIOUS, SICK) | default HEALTHY |
| next_inspection_at | date null | ≥ inspected date |
| notes | text | |

## diseases (catalog, seeded)
code (unique), name, is_quarantine, is_active, sort_order.
Seed: VARROOSIS Варроатоз; NOSEMOSIS Нозематоз; AFB Американский гнилец (quarantine);
EFB Европейский гнилец; CHALKBROOD Аскосфероз (известковый расплод); VIRAL Вирусные болезни;
WAX_MOTH Восковая моль; OTHER Другое.

## hive_diseases (cases)
hive_id, disease_id, detected_at (date), severity (LIGHT, MODERATE, SEVERE), symptoms, diagnosis,
status (SUSPECTED, CONFIRMED, TREATING, RESOLVED), resolved_at (date, required iff RESOLVED,
≥ detected_at), notes, created_by.

## treatments
hive_id, disease_id null, hive_disease_id null (same hive), treated_at (date), medication (required),
dosage, method, performed_by (FK users), result, next_treatment_date (≥ treated_at), notes.

## feedings
hive_id, fed_at (date), feed_type (SUGAR_SYRUP, CANDY, HONEY, PROTEIN, POLLEN_SUBSTITUTE, MEDICATED,
OTHER), quantity numeric(10,2) > 0, unit (KG, G, L, ML, PCS), reason, result, next_feeding_date
(≥ fed_at), notes, created_by.

## tasks (reminders)
hive_id null, kind (INSPECTION, TREATMENT, FEEDING, OTHER), title, due_date, status (OPEN, DONE,
CANCELLED), source_type, source_id, created_by, completed_at, completed_by.
Index (status, due_date).

## Derived hive state
- `hives.last_inspection_at` = max(inspected_at); `next_inspection_at` from the latest inspection.
- `bee_families.strength` = strength of the newest inspection when it is the latest.
- `hives.status` SICK/QUARANTINE ⇄ ACTIVE per FR-010.
