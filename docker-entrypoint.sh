#!/bin/sh
# Production start: apply migrations once, then run the command (uvicorn).
# The lock stops two starts from migrating at the same time. If the migration
# fails the container exits, so the app never runs on a half-migrated schema.
set -e

echo "Running Alembic migrations..."
flock /app/data/.migrate.lock alembic upgrade head

exec "$@"
