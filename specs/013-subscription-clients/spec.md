# Feature Specification: Subscription clients (one server, a branded copy per client)

**Feature Branch**: `013-subscription-clients` · **Created**: 2026-10-17 · **Status**: Implemented
**Input**: owner's answers (2026-10-17): sell as a subscription, servers stay with the owner; each client gets a
fully branded app (name, logo, colour, domain, bot); unpaid → fully blocked; up to 5 clients in the first year.

## Model
- One **installation per client**: own PostgreSQL database, uploads, domain, HTTPS certificate, Telegram bot and
  `.env` (`clients/<slug>.env` on the server, never in Git). Clients never share data.
- Same code and Docker images for everyone (`beekeeping-backend|frontend|bot:latest`, built once by
  `deploy/client.sh build`); the brand is runtime configuration, so no per-client builds.
- One shared edge nginx (`deploy/edge`, container `bee-edge`, ports 80/443) routes each domain to
  `<slug>-backend` / `<slug>-frontend` on the external Docker network `bee-edge`; certificates by host certbot
  (webroot `/var/www/certbot`). A stopped client does not stop nginx (runtime DNS resolver).

## Brand (`BRAND_*` settings)
- `BRAND_NAME`, `BRAND_SUBTITLE`, `BRAND_COLOR` (#rrggbb), `BRAND_LOGO` (PNG path; default = Fayzi Umar logo).
- Public `GET /api/branding` → name, subtitle (translated), colour + lighter/deeper shades, logo/icon URLs (cache
  key = logo file mtime), subscription state. `/api/branding/logo.png`, `icon-{64|180|192|512}.png`,
  `icon-maskable-512.png`, `manifest.webmanifest` are generated from the logo with Pillow.
- Frontend loads it before the first render (4 s timeout → built-in defaults): title, CSS variables
  `--gold`, `--gold-light`, `--gold-deep`, `--gold-rgb`; logo and name on login, home, state screens.
  index.html uses the server manifest and icons; the service worker caches only `/`.
- Brand also in PDFs/XLSX (author, subtitle), QR labels, admin invite text, bot login prompt and test reminder.

## Subscription
- `SUBSCRIPTION_UNTIL` (date, inclusive; empty = no limit), `SUBSCRIPTION_CONTACT` (phone, @username, URL, e-mail).
- After the date every `/api/*` except `/api/health` and `/api/branding*` answers **402** «Подписка закончилась…».
  The frontend shows the full-screen «Подписка закончилась» with the contact (also on any 402 while open);
  the bot reminders stop by themselves (dispatch gets 402). Data is kept; extending reopens access.
- 7 days before the end the admin sees a warning on the home screen.

## Operations (`deploy/client.sh`)
`build`, `add SLUG DOMAIN` (generated DB password and JWT secret, 30 days trial), `logo`, `start` (certificate +
site + up; the bot only when a token is set), `update [all]`, `extend SLUG +1year|DATE`, `block`, `list`,
`backup [all]` (30 days kept), `logs`, `stop`, `renew` (cron), `adopt SLUG` — moves the old single install
(root `.env`) into clients while keeping the Docker project name `beekeeping` and therefore its volumes.

## Out of scope
Online payments and automatic invoices; a central owner dashboard; several clients in one database.
