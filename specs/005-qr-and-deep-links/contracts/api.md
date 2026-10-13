# API — stage 5

## GET /api/hives/{id}/qr  (any role)
```json
{ "hive_id": "…", "hive_number": "27", "apiary_name": "Пасека", "code": "hive_…",
  "deep_link": "https://t.me/bot/app?startapp=hive_…" | null,
  "content": "<what the QR encodes>", "deep_link_ready": true,
  "svg_data_uri": "data:image/svg+xml;…", "print_count": 0, "last_printed_at": null }
```

## POST /api/hives/{id}/qr  (CAN_WRITE)
Ensures the QR exists; idempotent; same body as GET.

## GET /api/qr/resolve?code=…  (any role)
```json
{ "status": "found" | "unknown" | "invalid", "hive_id": "…" | null, "hive_number": "27" | null,
  "apiary_name": "…" | null, "is_archived": false, "can_register": false }
```
`unknown` returns `hive_id` = the identifier from the code; `can_register` is true for ADMIN/BEEKEEPER.

## POST /api/qr/labels  (CAN_WRITE)
```json
{ "hive_ids": ["…"], "apiary_id": "…", "blank_count": 0, "delivery": "download" | "telegram" }
```
`download` → `application/pdf` attachment. `telegram` → `{ "sent": true, "labels": 5 }`.
Errors: 422 nothing selected / too many; 409 bot not configured; 502 Telegram refused.

## POST /api/hives (changed)
Optional `id` (uuid) — register a hive under a pre-printed QR. 409 if taken.
