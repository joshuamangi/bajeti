# Migrations

## Access your running container

docker exec -it bajeti_dev bash

## Inside container, run the migration

alembic upgrade head

## Test specific migration

alembic upgrade 2ffc2b03c4bf

## Rollback if needed

alembic downgrade -1

## Check for duplicate allocations first

SELECT budget_id, category_id, COUNT(*)
FROM allocations
GROUP BY budget_id, category_id
HAVING COUNT(*) > 1;

## Production

docker compose run --rm bajeti_app alembic stamp e8b935ff95f0
docker compose run --rm bajeti_app alembic upgrade head
