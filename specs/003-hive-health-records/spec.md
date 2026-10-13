# Feature Specification: Hive health records — inspections, diseases, treatments, feedings

**Feature Branch**: `003-hive-health-records`

**Created**: 2026-10-13

**Status**: Ready for planning

**Input**: Stage 3 of `docs/requirements.md` (sections 10–13, 25, 35): "Создать: inspections; health; diseases; treatments; feedings."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record a hive inspection at the apiary (Priority: P1)

A beekeeper stands at a hive with a phone, opens the hive card, taps «Осмотр», fills in what they
see (strength, frames, brood, honey, pollen, queen seen or not, eggs, queen cells, swarming signs,
food level, temperament, health) and saves. The hive card immediately shows the date of this
inspection and when the next one is due, and the family strength reflects what was just observed.

**Why this priority**: Inspections are the daily core of beekeeping and the main scenario of the
whole product («проводит осмотр → добавляет данные → сохраняет»). Every other record in this stage
is triggered by what an inspection reveals.

**Independent Test**: Create a hive with a family, record an inspection, and verify the hive shows
the new last/next inspection dates, updated strength, and the inspection in its timeline.

**Acceptance Scenarios**:

1. **Given** a hive with a living family, **When** the beekeeper saves an inspection with strength
   «Сильная», 10 frames (6 brood, 3 honey, 1 pollen) and queen seen, **Then** the inspection is
   stored, the hive's last inspection date is the inspection date, the next inspection date is set
   (7 days later unless the beekeeper chose another date), and the family strength is «Сильная».
2. **Given** an inspection form, **When** brood + honey + pollen frames exceed the total frames, or
   any count is negative, or the date is in the future, **Then** saving is refused with a clear
   Russian message naming the field.
3. **Given** an inspection where the queen was not seen and no eggs were found, **When** it is
   saved, **Then** the result screen warns that the hive may be queenless and offers to mark it,
   without changing the queen record automatically.
4. **Given** an archived or empty hive, **When** someone tries to record an inspection, **Then** it
   is refused with an explanation.
5. **Given** an inspection was saved with a typo, **When** a beekeeper corrects it, **Then** the
   correction is saved and recorded in the hive history with old and new values.

---

### User Story 2 - Track a disease case from suspicion to recovery (Priority: P2)

The beekeeper notices symptoms and opens a disease case on the hive, choosing the disease from a
catalog (varroosis, nosemosis, American and European foulbrood, chalkbrood, viral diseases, wax
moth, other), with severity and symptoms. The case moves through «Подозрение → Подтверждено →
Лечение → Вылечено». While a case is confirmed or being treated, the hive is shown as sick; for
quarantine diseases (American foulbrood) it is shown as quarantined. When all cases are resolved,
the hive returns to normal.

**Why this priority**: Health status directly drives decisions (treat, isolate, merge) and the
dashboard counters «Больные». It depends on hives existing but not on treatments.

**Independent Test**: Open a confirmed varroosis case on a hive, check the hive shows «Болеет»,
resolve the case, check the hive is «Активный» again and both events appear in the timeline.

**Acceptance Scenarios**:

1. **Given** a healthy active hive, **When** a case is opened with status «Подтверждено», **Then**
   the hive status becomes «Болеет» and the change appears in its history.
2. **Given** a case for a quarantine disease, **When** it is confirmed, **Then** the hive status
   becomes «Карантин».
3. **Given** a hive with one open case, **When** that case is resolved with a resolution date,
   **Then** the hive status returns to «Активный»; **Given** two open cases, resolving one keeps the
   hive sick.
4. **Given** a resolved case, **When** someone tries to reopen it or set a resolution date before
   the detection date, **Then** it is refused.
5. **Given** a case status «Подозрение», **Then** the hive status does not change (suspicion alone
   does not mark a hive sick).

---

### User Story 3 - Record treatments with automatic reminders (Priority: P2)

The beekeeper records a treatment: date, medication, dosage, method, which disease or case it
targets, result, and the date of the next treatment. Linking a treatment to a case moves the case to
«Лечение». When a next treatment date is given, the system creates a reminder task for that date
which appears in the hive card and in the list of upcoming tasks, and is closed when the next
treatment is recorded.

**Why this priority**: Treatment schedules (e.g. repeated varroa treatments) are easy to forget and
the requirements explicitly ask for automatic reminders.

**Independent Test**: Record a treatment with a next treatment date and check that a reminder task
exists for that hive and date; record the follow-up treatment and check the reminder is closed.

**Acceptance Scenarios**:

1. **Given** a hive with an open varroosis case, **When** a treatment linked to that case is saved,
   **Then** the treatment is stored with the user who performed it and the case status is
   «Лечение».
2. **Given** a treatment with next treatment date D, **When** it is saved, **Then** an open reminder
   «Повторная обработка» due on D exists for the hive.
3. **Given** an open treatment reminder for a hive, **When** a new treatment is recorded on that
   hive, **Then** the earlier open treatment reminder is marked done.
4. **Given** a next treatment date earlier than the treatment date, **Then** saving is refused.

---

### User Story 4 - Record feedings (Priority: P3)

The beekeeper records a feeding: date, feed type (sugar syrup, candy, honey, protein patty, pollen
substitute, medicated feed, other), quantity with unit, reason, result and an optional next feeding
date which creates a reminder the same way as treatments.

**Why this priority**: Important in spring and autumn, but less time-critical than health.

**Independent Test**: Record a feeding of 2 l sugar syrup with a next feeding date and verify it
appears in the timeline and a feeding reminder exists.

**Acceptance Scenarios**:

1. **Given** a hive with a family, **When** a feeding of 2 «л» of «Сахарный сироп» is saved,
   **Then** it appears in the hive timeline with quantity and unit.
2. **Given** a quantity of zero or below, **Then** saving is refused.

---

### User Story 5 - One timeline per hive (Priority: P2)

On the hive card the beekeeper sees one chronological timeline mixing inspections, disease cases
(opened and resolved), treatments, feedings and earlier events (queen replacement, family change,
number change), newest first, each with date, author and a one-line summary — matching the example
in the requirements (section 25).

**Why this priority**: This is how the product answers «что происходило с ульем»; it ties all
records of this stage together.

**Independent Test**: Create one record of each kind on a hive and check the timeline lists all of
them in date order with readable summaries.

**Acceptance Scenarios**:

1. **Given** a hive with an inspection on 05.10, a treatment on 20.09 and a queen replacement on
   10.04, **When** the timeline is opened, **Then** they appear in that order with summaries such as
   «Осмотр — Сила: сильная, Рамки: 10», «Обработка — Варроатоз», «Замена матки — M-105 → M-205».

### Edge Cases

- Two people inspect the same hive on the same day: both inspections are kept; the hive's last
  inspection is the latest by date and time.
- An inspection dated earlier than the current last inspection does not move the last/next
  inspection dates backwards.
- Correcting the date of the latest inspection recalculates the hive's last inspection date.
- A treatment linked to a case of another hive is refused.
- A disease removed from use in the catalog stays visible on old cases.
- Viewer accounts can read everything in this stage but cannot create or change records.
- Records are never deleted; mistakes are corrected and the correction is audited.

## Requirements *(mandatory)*

### Functional Requirements

**Inspections**

- **FR-001**: Users with write access (administrator, beekeeper, assistant) MUST be able to record
  an inspection for a non-archived hive that has a living family.
- **FR-002**: An inspection MUST capture: date and time, author, strength, total/brood/honey/pollen
  frames, queen present, queen condition, egg laying, queen cells, swarming signs, food level,
  aggressiveness, health status, notes, and the chosen next inspection date.
- **FR-003**: The system MUST reject negative frame counts, brood+honey+pollen greater than total
  frames, and dates in the future.
- **FR-004**: Saving an inspection MUST update the hive's last inspection date (only if the new
  inspection is the latest) and next inspection date (chosen date, otherwise 7 days after the
  inspection), and set the current family strength to the observed strength, recording these
  changes in the hive history.
- **FR-005**: When the queen is not seen and no eggs are found, the system MUST warn the user that
  the hive may be queenless; it MUST NOT alter the queen record by itself.
- **FR-006**: Inspections MUST be correctable by write users; each correction MUST be audited.

**Diseases**

- **FR-007**: The system MUST provide a disease catalog pre-filled with: varroosis, nosemosis,
  American foulbrood, European foulbrood, chalkbrood, viral diseases, wax moth, other. Each entry
  states whether it requires quarantine. Administrators and beekeepers MAY add catalog entries.
- **FR-008**: Write users MUST be able to open a disease case on a hive with: disease, detection
  date, severity (light / moderate / severe), symptoms, diagnosis, status, notes.
- **FR-009**: Case status MUST follow SUSPECTED → CONFIRMED → TREATING → RESOLVED (skipping forward
  allowed; going back from RESOLVED not allowed). RESOLVED requires a resolution date not earlier
  than the detection date.
- **FR-010**: The hive status MUST become «Болеет» while it has at least one CONFIRMED or TREATING
  case, «Карантин» if any such case is for a quarantine disease, and return to «Активный» when no
  such case remains (only if the hive was set sick/quarantined by this rule's statuses).

**Treatments**

- **FR-011**: Write users MUST be able to record a treatment with: date, disease (optional), linked
  case (optional, same hive only), medication, dosage, method, performer (the current user), result,
  next treatment date (optional, not before the treatment date), notes.
- **FR-012**: Linking a treatment to a SUSPECTED or CONFIRMED case MUST move the case to TREATING.
- **FR-013**: A next treatment date MUST create an open reminder task for that hive and date; a new
  treatment on the hive MUST close earlier open treatment reminders.

**Feedings**

- **FR-014**: Write users MUST be able to record a feeding with: date, feed type, quantity (> 0),
  unit (kg, g, l, ml, pcs), reason, result, next feeding date (optional), notes; a next feeding date
  MUST create a reminder like FR-013 (closing earlier open feeding reminders on new feeding).

**Timeline, reminders, permissions**

- **FR-015**: Each hive MUST have a timeline combining all records of this stage with the hive
  history events from stage 2, newest first, each item having a date, kind, author and summary.
- **FR-016**: Users MUST be able to see open reminders (per hive and across all hives) and mark a
  reminder done.
- **FR-017**: Viewers MUST be able to read all records but not create or change them. Only
  administrators and beekeepers may change the disease catalog.
- **FR-018**: No record of this stage is ever physically deleted.
- **FR-019**: The home screen MUST show how many hives need inspection (next inspection date today
  or earlier, or never inspected while having a family).

### Key Entities

- **Inspection**: one visit to one hive at a moment in time with the observations listed in FR-002;
  belongs to a hive and an author.
- **Disease**: catalog entry — name, code, quarantine flag, active flag.
- **Disease case (hive disease)**: one occurrence of a disease in a hive — detection date,
  severity, symptoms, diagnosis, status, resolution date.
- **Treatment**: one application of a medication to a hive, optionally for a disease/case, with the
  performer and the planned next treatment.
- **Feeding**: one feeding of a hive with feed type, quantity and unit.
- **Task (reminder)**: something to do for a hive by a due date (repeat treatment, next feeding);
  open/done/cancelled; created automatically from records; later used by Telegram notifications
  (stage 8).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A beekeeper can record a full inspection on a phone in under 90 seconds, with at most
  one screen to scroll and no typing required except notes.
- **SC-002**: After saving any record, the hive card shows the updated state (last/next inspection,
  strength, status, reminders) without manual refresh.
- **SC-003**: 100% of invalid inputs listed in FR-003, FR-009, FR-011, FR-014 are rejected with a
  message in Russian that names the problem.
- **SC-004**: Every record created or corrected in this stage is visible in the hive timeline with
  its author.
- **SC-005**: Every treatment with a next date has exactly one open reminder until the follow-up
  treatment is recorded.

## Assumptions

- Default interval to the next inspection is 7 days (typical in season); the beekeeper can change
  it per inspection. Seasonal intervals and winter mode come with wintering (stage 4).
- Severity uses three levels (light / moderate / severe).
- «Помощник» (assistant) may record inspections, diseases, treatments and feedings — they are field
  work; structural changes (hives, queens, families) stay with beekeepers.
- Photos on inspections/treatments are delivered in stage 9; the forms leave room for them.
- Offline saving of inspections is delivered later (requirements section 31); this stage requires a
  connection.
- Reminders are only stored and shown in this stage; sending them via the Telegram bot is stage 8.
