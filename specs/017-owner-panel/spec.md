# Feature Specification: Owner panel for the subscription

**Feature Branch**: `017-owner-panel` · **Created**: 2026-10-18 · **Status**: Implemented
**Input**: owner (2026-10-18): «Для подписки — ваша панель владельца»: all clients in one window, who uses how
much, who pays when, extending with one button (until now: commands on the server).

## Per installation
- `installation_state` (one row): paid-until date set from the panel or the server command. When present it wins
  over SUBSCRIPTION_UNTIL from the .env (the starting value). Cached 15 s for the per-request check; if the database
  cannot be read the .env value is used.
- Owner API `/api/owner/*`, header `X-Owner-Token` = OWNER_TOKEN (≥ 32 chars, per client, made by deploy/client.sh;
  empty = API off → 404; wrong → 401; constant-time compare). Not routed by the public nginx (404); reached over the
  Docker network. Works while the client is blocked.
  - `GET /api/owner/stats`: brand, subscription (until, days left, active, source env|panel|none, contact), active
    hives, apiaries, users active/total, last login, last change, honey this year (kg), schema revision.
  - `PUT /api/owner/subscription {until: date|null}` (null = no limit); audit `installation / subscription_set`.
- Server command: `python -m app.utils.subscription show | set DATE | set none`.

## Panel (`app.owner_panel.main`, container `bee-owner`, same image)
- Password login (OWNER_PASSWORD; 5 wrong → 15 min lock per IP + nginx limit), signed session cookie 12 h
  (HttpOnly, SameSite=Strict, Secure), form token on every action, no framing, no caching, noindex.
- Clients from clients/*.env (read-only mount): one card each — brand colour and name, domain, status (paid / N days
  left / closed / not answering / no key), paid until (and whether set from the panel), hives, apiaries, users, honey,
  last login and change; buttons +1 month, +1 year (from the current end, or from today when passed), no limit,
  close access, until a chosen date.
- Russian only (owner tool); not part of the i18n catalogs.

## Server
`./deploy/client.sh owner admin.example.tj` — creates deploy/owner.env (password shown once), adds OWNER_TOKEN to
clients without one (recreates their backend), starts the panel, certificate and site. `owner-password` — new
password. `extend` / `block` / `list` use the client's database through the server command (and keep the .env in
step); `extend SLUG none` — no limit.
