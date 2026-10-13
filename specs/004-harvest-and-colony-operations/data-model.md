# Data model — stage 4

| table | key columns | rules |
|---|---|---|
| honey_harvests | hive_id, apiary_id (at harvest time), harvest_date, harvest_year, harvest_number, honey_type, frames_count, weight_kg numeric(8,2), price_per_kg numeric(10,2) null, total_value GENERATED (weight×price), created_by | weight > 0, price ≥ 0, frames ≥ 0; unique (hive_id, harvest_year, harvest_number) |
| other_products | product_type enum (WAX, PROPOLIS, BEE_BREAD, POLLEN, ROYAL_JELLY, QUEENS, COLONIES, PACKAGES), collected_at, quantity numeric(10,2), unit (KG,G,L,ML,PCS), hive_id null, apiary_id null, price_per_unit null, total_value GENERATED, notes, created_by | quantity > 0, price ≥ 0 |
| swarms | hive_id, swarm_date, swarm_count, captured, new_hive_id null, new_queen_id null, actions, notes, created_by | count ≥ 1; new_hive only if captured |
| hive_splits | source_hive_id, new_hive_id, split_date, queen_id null, notes, created_by | source ≠ new |
| hive_merges | target_hive_id, merge_date, kept_queen_id null, notes, created_by | |
| hive_merge_sources | merge_id, hive_id (PK both) | sources merged away (target not listed unless it was also a source… target is stored on the merge only) |
| hive_movements | hive_id, from_apiary_id, to_apiary_id, movement_date, reason, notes, performed_by | from ≠ to |
| winterings | hive_id, season ('2026/2027'), pre_winter_strength, food_kg numeric(6,2), frames_count, queen_condition text, pre_winter_treatment, winter_location, start_date, end_date null, spring_strength null, result enum null (STRONG, WEAK, DIED), notes, created_by | unique (hive_id, season); end ≥ start; result iff end_date |
