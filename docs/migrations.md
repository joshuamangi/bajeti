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

Status: not yet in production. After the deploy, check `alembic current` shows a7d3c2f19b40 and record
the date here.

Rollback (drops the snapshots and the two indexes; no other data is touched):

docker compose exec bajeti_app alembic downgrade 186f1cc1a7ca
