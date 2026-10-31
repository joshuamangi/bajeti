# Migrations

## Access your running container

docker exec -it bajeti_dev bash

## Inside container, run the migration

alembic upgrade head

## Test specific migration

alembic upgrade fb0f9940d407

## Rollback if needed

alembic downgrade -1

## Check for duplicate allocations first

SELECT budget_id, category_id, COUNT(*)
FROM allocations
GROUP BY budget_id, category_id
HAVING COUNT(*) > 1;

## Production

The deploy workflow already runs `alembic upgrade head` after every merge, so normally nothing
needs to be done by hand. To check where production is:

docker compose exec bajeti_app alembic current

Do NOT run `alembic stamp` to a newer revision. Stamping only rewrites the version number and skips the
migration itself. Production was at 877adbb8bce2 (no `targets` table) before the targets feature, so
the deploy that includes migrations 9b38fdc94e38 and 186f1cc1a7ca must run `upgrade head` to create the
table and fill it. Stamp only when the database already has the schema change but the version number
is missing.

Rollback of the targets feature (removes the backfilled rows, then the table):

docker compose exec bajeti_app alembic downgrade 877adbb8bce2

## Allocation snapshots (Analytics), a7d3c2f19b40

Adds `allocation_snapshots`, records the current month from today's allocations, and adds two indexes
(`ix_expenses_user_month_category`, `ix_transfers_user_month`). Earlier months get no snapshot (owner
decision: analytics starts from the migration date). Tested on a scratch database with the production
schema: upgrade, downgrade (expenses kept), upgrade again; one head.

Status: in production since 2026-10-28 (deploy of PR #145; the deploy log shows
`Running upgrade 186f1cc1a7ca -> a7d3c2f19b40` and `alembic current` = a7d3c2f19b40). Not checked on the
Pi by hand.

Rollback (drops the snapshots and the two indexes; no other data is touched):

docker compose exec bajeti_app alembic downgrade 186f1cc1a7ca

## Recurring expenses, b2c4e6f8a1d3, and payment capture, c3d5f7a9b1e2

New tables only: `recurring_expenses` and `recurring_runs`, then `pending_payments` and `payee_rules`.
No existing rows change. Both tested on a scratch database (upgrade, downgrade, upgrade; one head).

Status: in production since 2026-10-29 (deploy of PR #147; the deploy log shows
`Running upgrade a7d3c2f19b40 -> b2c4e6f8a1d3`, `b2c4e6f8a1d3 -> c3d5f7a9b1e2` and `alembic current` =
c3d5f7a9b1e2). Not checked on the Pi by hand.

Rollback (drops the four tables and everything in them):

docker compose exec bajeti_app alembic downgrade a7d3c2f19b40

## Default budget, d4e6a8c0b2f3

Adds `budgets.is_default` (false for every existing budget), so nothing changes until the owner
stars a budget on the Budgets screen. Tested on a scratch database with today's schema: upgrade,
downgrade (budgets kept), upgrade again; one head.

Status: in production since 2026-10-29 (deploy of PR #148; the deploy log shows
`Running upgrade c3d5f7a9b1e2 -> d4e6a8c0b2f3` and `alembic current` = d4e6a8c0b2f3). Not checked on the
Pi by hand.

Rollback (drops the column; budgets are kept):

docker compose exec bajeti_app alembic downgrade c3d5f7a9b1e2

## Owner flag and reset links, e7a1c3b5d9f2

Adds `users.is_owner` (false for everyone) and the `password_reset_links` table (one-time links the
owner creates for a locked-out member; only a sha256 of the token is stored). The owner is set once
with `python -m cli.set_owner`. How this migration was tested before deploy is not recorded here.

Status: in production since 2026-10-31 (deploy of PR #153; the deploy log shows
`Running upgrade d4e6a8c0b2f3 -> e7a1c3b5d9f2` and `alembic current` = e7a1c3b5d9f2). Not checked on the
Pi by hand, and whether the owner flag has been set is unchecked.

Rollback (drops the table and the column; outstanding reset links stop working):

docker compose exec bajeti_app alembic downgrade d4e6a8c0b2f3

## Phone tokens, e5f7a9c1d3b4

Adds the `api_tokens` table for the iPhone Shortcut (hashed tokens, scope `payments:capture`). New
table only. Tested on a scratch database stamped at e7a1c3b5d9f2: upgrade, downgrade, upgrade again;
one head.

Status: in production since 2026-10-31 (deploy of PR #154; the deploy log shows
`Running upgrade e7a1c3b5d9f2 -> e5f7a9c1d3b4` and `alembic current` = e5f7a9c1d3b4). Not checked on the
Pi by hand.

Rollback (drops the table; every phone token stops working):

docker compose exec bajeti_app alembic downgrade e7a1c3b5d9f2
