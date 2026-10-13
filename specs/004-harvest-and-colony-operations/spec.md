# Feature Specification: Harvest and colony operations

**Feature Branch**: `004-harvest-and-colony-operations`

**Created**: 2026-10-13

**Status**: Ready for planning

**Input**: Stage 4 of `docs/requirements.md` (sections 14–19): honey, other products, swarming,
split, merge, movements, wintering.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record a honey harvest and see totals (Priority: P1)

After extracting honey from a hive the beekeeper taps «Мёд» on the hive card, enters the weight,
number of frames, honey type and price per kg. The value is calculated automatically. The hive card
shows how much honey the hive gave this year, and a honey page shows honey for the month, season,
year and all time, the average per hive and the most productive hive.

**Why this priority**: Honey is the main product and the main business result; it drives the
dashboard and the yearly report.

**Independent Test**: Record two harvests on two hives and check the per-hive year total, the
overall totals, the average per hive and the best hive.

**Acceptance Scenarios**:

1. **Given** a hive, **When** a harvest of 12.5 kg at 80 per kg is recorded, **Then** its value is
   1000 and it gets the next harvest number for that hive in that year (1, 2, 3…).
2. **Given** harvests in several months, **When** the honey page is opened for a year, **Then** it
   shows totals for the current month, the season (the selected year), the year, all time, kg by
   month, the average per producing hive and the best hive.
3. **Given** a weight of zero or less, a negative price or frame count, or a future date, **Then**
   saving is refused with a Russian message.

---

### User Story 2 - Move a hive to another apiary (Priority: P2)

The beekeeper takes hives to summer pasture: on the hive card they choose «Переместить», pick the
target apiary, date and reason. The hive keeps its identity (QR, history); if its number is taken
at the target apiary, they must give a new number.

**Why this priority**: Migratory beekeeping is common; movements must not break history.

**Independent Test**: Move a hive, check it appears in the target apiary with the same id and the
movement appears in its timeline with from/to apiaries.

**Acceptance Scenarios**:

1. **Given** a hive in apiary A, **When** it is moved to apiary B, **Then** the hive belongs to B,
   keeps its id, and a movement record with from A, to B, date, reason and performer exists.
2. **Given** the number is already used in B, **When** moving without a new number, **Then** it is
   refused with a message asking for a new number; with a new free number it succeeds and the number
   change is in history.
3. **Given** the same apiary as target, or an archived apiary, **Then** it is refused.

---

### User Story 3 - Swarm, split and merge colonies (Priority: P2)

- **Swarm**: the beekeeper records that a hive swarmed (date, number of swarms, captured or not,
  actions). A captured swarm can be settled into an existing empty hive or a new hive; that hive gets
  a new family of origin «Рой».
- **Split**: from hive 10 the beekeeper makes a new hive 35 (new number in the same apiary or an
  existing empty hive); the new hive gets a family of origin «Отводок», optionally a free queen
  (otherwise it is marked «Без матки»). The source hive keeps living.
- **Merge**: hives 15 and 18 are merged into one (one of them or a new hive 40). The beekeeper
  chooses which queen to keep; other queens are marked replaced. Merged-away hives become archived
  «Объединён» with their families closed, never deleted.

**Why this priority**: These operations change colony structure; history must show where each
colony came from.

**Independent Test**: Perform each operation and check the resulting hives, families, queens,
statuses and links in timelines.

**Acceptance Scenarios**:

1. **Given** hive 10 with a family, **When** split into new hive 35 without a queen, **Then** hive
   35 exists with a family «Отводок» and status «Без матки», and the split links 10 → 35 in both
   timelines.
2. **Given** hives 15 and 18 with queens Q15 and Q18, **When** merged into 15 keeping Q18, **Then**
   15 has Q18 as queen, Q15 is «Заменена», 18 is archived «Объединён» with its family closed
   «Объединена», and the merge record lists 15 as target and 18 as source.
3. **Given** a merge into a new hive 40, **Then** 40 is created with a family of origin
   «Объединение», all sources are archived «Объединён».
4. **Given** a captured swarm settled into new hive 41, **Then** 41 has a family «Рой»; the
   swarming hive's timeline shows the swarm with a link to 41.
5. **Given** a target hive that is not empty, or a source that is archived, or fewer than two hives
   in a merge, **Then** the operation is refused.

---

### User Story 4 - Wintering (Priority: P3)

In autumn the beekeeper puts a hive into winter: season, strength, food in kg, frames, queen
condition, pre-winter treatment, winter location, start date. In spring they close the wintering
with end date, spring condition and result. If the colony died, its family is closed as dead and the
hive becomes empty.

**Why this priority**: Wintering outcome is a key yearly metric but happens once a year.

**Independent Test**: Start and finish a wintering for a hive with each result and check the hive
and family state.

**Acceptance Scenarios**:

1. **Given** a hive with a family, **When** wintering for season 2026/2027 is started, **Then** it is
   stored; a second wintering for the same hive and season is refused.
2. **Given** an open wintering, **When** it is finished with result «Погибла», **Then** the family is
   closed «Погибла», the hive is «Пустой», the queen (if any) is «Погибла».
3. **Given** an end date before the start date, **Then** it is refused.

---

### User Story 5 - Other products (Priority: P3)

The beekeeper records other products: wax, propolis, bee bread, pollen, royal jelly, queens,
colonies, packages — with quantity, unit, date, optional hive and price.

**Independent Test**: Record 1.2 kg of wax at 150 and see it in the products list with value 180.

**Acceptance Scenarios**:

1. **Given** a product entry with quantity > 0, **Then** it is stored with computed value.
2. **Given** quantity ≤ 0 or a negative price, **Then** it is refused.

### Edge Cases

- Harvest numbers restart every calendar year per hive.
- A hive moved mid-season keeps all its harvests; per-apiary totals use the apiary at harvest time.
- A merge that keeps a queen from a source hive moves her into the target hive with a closed
  assignment period in the source.
- Operations on archived hives are refused; nothing is physically deleted.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Write users MUST record honey harvests (date, number auto per hive/year, honey type,
  frames ≥ 0, weight > 0, price per kg ≥ 0 optional); value = weight × price, computed, never typed.
- **FR-002**: The system MUST provide honey statistics: month, season (= selected year), year, all
  time, kg per month for a year, average per producing hive, most productive hive; and the current
  year's honey for each hive.
- **FR-003**: Write users MUST record other products of the 8 types from the requirements with
  quantity > 0, unit, optional hive/apiary and price; value computed.
- **FR-004**: Managers (admin, beekeeper) MUST be able to move a hive between non-archived
  apiaries; a movement record keeps from/to, date, reason, performer; number conflicts require a new
  free number.
- **FR-005**: Managers MUST record swarms; a captured swarm MAY be settled into an empty existing
  hive or a new hive, which gets a family of origin SWARM.
- **FR-006**: Managers MUST split a hive into a new or empty hive (family origin SPLIT, optional
  free queen, otherwise QUEENLESS); a split record links source and new hive.
- **FR-007**: Managers MUST merge ≥ 2 hives into one of them or a new hive, choosing the queen to
  keep; non-target sources become MERGED (archived) with families closed MERGED; queens not kept
  become REPLACED; a merge record links target and all sources.
- **FR-008**: Managers MUST start and finish winterings (one per hive per season); finishing with
  result DIED closes the family as DEAD, retires the queen as DEAD and marks the hive EMPTY.
- **FR-009**: All operations MUST be audited and appear in the hive timeline (and in both hives'
  timelines for splits, merges and settled swarms).
- **FR-010**: Validation errors MUST be reported in Russian naming the field.

### Key Entities

- **Honey harvest**: hive, date, number in year, honey type, frames, weight, price, value.
- **Other product**: type, date, quantity, unit, hive/apiary, price, value.
- **Swarm**: hive, date, count, captured, settled-into hive, new queen, actions.
- **Split**: source hive, new hive, date, queen given, notes.
- **Merge**: target hive, date, kept queen, sources (association), notes.
- **Movement**: hive, from apiary, to apiary, date, reason, performer.
- **Wintering**: hive, season, pre-winter strength, food kg, frames, queen condition, treatment,
  location, start/end dates, spring strength, result.

## Success Criteria *(mandatory)*

- **SC-001**: Recording a honey harvest takes under 30 seconds on a phone.
- **SC-002**: Honey totals on the honey page equal the sum of recorded harvests for the period
  (verified by tests) — no manual arithmetic.
- **SC-003**: After a split, merge or move, every affected hive's timeline explains what happened
  and links to the other hive(s).
- **SC-004**: No hive, family or queen record disappears as a result of any operation.

## Assumptions

- «Season» equals a calendar year for honey statistics; wintering seasons are labelled «YYYY/YYYY+1».
- Currency is not specified; values are shown without a currency sign (settings come with finances,
  stage 7).
- Honey types are free text with suggestions (разнотравье, акация, липа, гречиха, подсолнечник,
  горный, хлопковый, эспарцет).
- Selling honey and income are recorded in finances (stage 7); here only production is counted.
