# Feature Specification: Work without internet at the apiary

**Feature Branch**: `015-offline` · **Created**: 2026-10-18 · **Status**: Implemented
**Input**: owner (2026-10-18): «Работа без интернета на пасеке».

## What works without a connection
- Opening the app with the last signed-in profile (`fayzi-umar.user`, profile only — no token); the brand seen last
  time; the static app and brand images from the service worker.
- Hives, passports, last inspections (frame prefill), diseases, warehouse, apiaries and reminders from the phone's
  copy (TanStack Query persisted to IndexedDB, 14 days, per person; money/dashboard/CRM are not stored).
  While online the app loads all working hives (≤ 300) into the copy every 6 hours (`prefetchForOffline`).
- Scanning a hive QR: the hive id is read from the code and the cached hive opens; an uncached hive is explained.
- Saving inspections, feedings and treatments: kept in the outbox (`services/outbox.ts`, localStorage) with the time
  of saving and sent in order when the connection returns. Saving never waits longer than 15 s.

## Sync rules
- Every field record carries a `client_uid` made on the phone; the server returns the already saved record for a
  repeated uid (same hive) — no duplicates, stock written off once. Same uid for another hive → 409.
- Sending starts when the connection returns (failed request → offline; ping `/api/health` every 15 s; browser
  online event), after a quiet re-login, and every 30 s. A connection error stops the run; 401/402/429/5xx retry
  later; other refusals keep the record with the server's reason («Сохранено в телефоне» page: retry, open the
  hive, delete).
- Signing out with unsent records asks first (they are lost). The offline cache and profile are removed on sign-out.

## Limits
Telegram itself needs internet to start a Mini App; the app on the home screen opens offline. Other writes (hives,
honey, CRM, stock) need a connection.
