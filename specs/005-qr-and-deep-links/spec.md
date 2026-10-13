# Feature Specification: QR codes, scanner and Telegram deep links

**Feature Branch**: `005-qr-and-deep-links`

**Created**: 2026-10-13

**Status**: Ready for planning

**Input**: Stage 5 of `docs/requirements.md` (sections «QR», 22 QR SYSTEM, 23 QR SCANNER, API
`GET/POST /api/hives/{id}/qr`, acceptance «каждому улью создаётся QR; QR можно распечатать; QR можно
отсканировать телефоном; после сканирования открывается правильный улей»).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Every hive has a permanent QR code (Priority: P1)

Every hive automatically gets a QR code when it is created (existing hives get one by migration).
The QR contains only the hive's permanent identifier inside a Telegram deep link:
`https://t.me/<bot>/<app>?startapp=hive_<uuid>`. On the hive card the beekeeper opens «QR-код» and
sees the code, the hive number and the link.

**Why this priority**: The QR is the entry point of the main field workflow (walk up to a hive →
scan → passport → inspection).

**Independent Test**: Create a hive, open its QR, change the number, the queen, the family and the
apiary; the QR content stays identical.

**Acceptance Scenarios**:

1. **Given** a new hive, **Then** it has a QR whose payload is `hive_<its uuid>`.
2. **Given** a hive whose number, queen, family, strength, health or apiary changed, **Then** its
   QR payload is unchanged.
3. **Given** the bot username (and optionally the Mini App short name) is configured, **Then** the
   QR contains the t.me deep link; **Given** it is not configured, **Then** the app warns that
   printed codes will open only from the in-app scanner and suggests configuring it before printing.

---

### User Story 2 - Print QR labels (Priority: P1)

The beekeeper prints labels: one hive, all hives of an apiary, and optionally blank labels for
hives that will be registered later. Labels are an A4 PDF (12 per page) with the QR, the hive
number and the apiary. Inside Telegram on a phone the PDF is sent by the bot to the user's chat
(from there it can be forwarded to a printer or computer); in a browser it is downloaded.

**Independent Test**: Request labels for an apiary with 3 hives and 2 blank labels; the PDF has 5
labels; the hives' print counters increase and their history shows «Напечатан QR-код».

**Acceptance Scenarios**:

1. **Given** hives are selected, **When** labels are requested, **Then** a PDF with one label per
   hive is produced, sorted by hive number.
2. **Given** blank labels are requested, **Then** each has a fresh, unused identifier.
3. **Given** nothing is selected, **Then** the request is refused with a Russian message.
4. **Given** delivery to Telegram and the bot is not configured or Telegram refuses, **Then** a
   clear Russian error is shown and nothing is marked as printed.
5. A viewer cannot print labels (CAN_WRITE only).

---

### User Story 3 - Scan a hive (Priority: P1)

The «Сканер» button in the bottom navigation opens the phone camera (Telegram native scanner).
After a QR is read the app opens the right hive passport. Outside Telegram (computer) a field lets
the user paste a code or link.

**Acceptance Scenarios**:

1. **Given** a hive QR, **When** it is scanned, **Then** the hive card opens (also for archived hives,
   which show their history).
2. **Given** a QR in our format whose hive does not exist, **Then** «Улей не найден» is shown and an
   ADMIN/BEEKEEPER is offered «Зарегистрировать улей с этим QR»; other roles are told to ask an
   administrator.
3. **Given** a QR that is not a hive QR (a website, random text), **Then** «Это не QR-код улья» is
   shown with a «Сканировать снова» button.
4. Accepted inputs: the t.me link, a link with `startapp=`/`tgWebAppStartParam=`, `hive_<uuid>`,
   a bare UUID, or an app URL `/hives/<uuid>`.

---

### User Story 4 - Open a hive from a deep link (Priority: P1)

When the phone's own camera scans the QR (outside Telegram), Telegram opens the Mini App with
`start_param = hive_<uuid>`. After login the app goes straight to that hive (same resolution as the
scanner, including «Улей не найден»).

---

### User Story 5 - Register a hive from an unknown QR (Priority: P2)

An administrator scans a blank label, taps «Зарегистрировать улей с этим QR», fills the usual new
hive form, and the new hive gets exactly that UUID, so the label already stuck on the hive works.

**Acceptance Scenarios**:

1. **Given** an unused identifier, **When** a hive is created with it, **Then** the hive's id is
   that identifier and its QR payload matches the label.
2. **Given** the identifier already belongs to a hive, **Then** creation is refused: «Этот QR уже
   привязан к улью №…».

### Edge Cases

- The QR is never regenerated with a different payload: `POST /api/hives/{id}/qr` is idempotent.
- Hives created by operations (split, swarm) also get a QR.
- Up to 300 hives and 60 blank labels per PDF.

## Requirements *(mandatory)*

- **FR-001** `qr_codes` table: one row per hive (unique hive_id, unique code), print counter and
  last print time.
- **FR-002** `GET /api/hives/{id}/qr` returns payload, deep link, readiness flag and an SVG image.
- **FR-003** `POST /api/hives/{id}/qr` ensures the QR exists (idempotent).
- **FR-004** `GET /api/qr/resolve?code=` → `found | unknown | invalid`, with `can_register`.
- **FR-005** `POST /api/qr/labels` → PDF download or delivery by the bot to the current user.
- **FR-006** `HiveCreate.id` (optional) to register a hive under a pre-printed identifier.
- **FR-007** Frontend: scanner page (Telegram `showScanQrPopup`, manual fallback), `/open?code=`
  resolver page, start_param routing, QR sheet on the hive card, «QR-наклейки» page.
- **FR-008** Printing writes `qr_printed` to the hive history.

## Success Criteria

- Scan → hive card in ≤ 2 taps from any screen.
- QR payload unchanged after every stage 2–4 operation (tested).
