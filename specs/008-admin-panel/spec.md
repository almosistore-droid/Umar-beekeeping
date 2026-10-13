# Feature Specification: Admin panel — access, invitations, system overview, activity log

**Feature Branch**: `008-admin-panel` · **Created**: 2026-10-14 · **Status**: Ready for planning
**Input**: Owner's request (2026-10-14): «Админ-панель: доступ и добавление новых пользователей; вся
информация мини-аппа». Not one of the 10 numbered stages; it brings forward parts of stage 9
(permissions, audit) for the ADMIN role.

## User Scenarios & Testing

### US1 Add a user in advance (P1)
The admin adds a person by Telegram ID or @username, chooses a role and an optional note (who it is).
When that person opens the Mini App for the first time they get this role at once (instead of
«Наблюдатель»). If the person already uses the app, their role is changed immediately. The admin can
share an invitation message (link to the bot) and revoke a pending invitation. Invitations expire
after 30 days.
**Acceptance**: invitation by ID matches before username; username is case-insensitive and «@» is
ignored; a used/revoked/expired invitation gives nothing; ADMIN_TELEGRAM_IDS still wins; a second
pending invitation for the same ID/username is refused; everything is audited.

### US2 Access (P1)
Users list: role, blocked/allowed, last visit. Block / unblock and change role (not for oneself).
A blocked user cannot log in or use a token.

### US3 Everything about the app (P1)
One screen: system (environment, time zone, currency, bot configured, QR deep links ready,
database size, server time), users by role (active / blocked / pending invitations), and totals of
every kind of record: apiaries, hives, families, queens, inspections, diseases, treatments,
feedings, reminders, honey (kg), products, operations, customers, sales, orders, expenses,
audit events.

### US4 Activity log (P1)
All changes across the system, newest first: when, who, what (entity and action), which hive; filter
by user and by section; load more.

All admin endpoints: ADMIN only.
