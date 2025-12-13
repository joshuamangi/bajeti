# Migrations

## Access your running container

docker exec -it bajeti_dev bash

## Inside container, run the migration

alembic upgrade head

## Test specific migration

alembic upgrade 2ffc2b03c4bf

## Rollback if needed

alembic downgrade -1

## Production

docker compose run --rm bajeti_app alembic current
docker compose run --rm bajeti_app alembic stamp 72bb1cfa160c
