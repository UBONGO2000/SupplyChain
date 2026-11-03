#!/bin/sh
# Container entrypoint: make the schema current, optionally seed a demo
# dataset, then hand over to the CMD (uvicorn).
set -eu

echo "Applying database migrations..."
alembic upgrade head

if [ "${CREATE_DEMO_USER:-false}" = "true" ]; then
  echo "Creating/rotating the demo account..."
  python -m cli create-demo-user
fi

if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  echo "Seeding demo data..."
  # Never block startup on demo data: the API is useful even on an empty DB.
  python -m cli seed-demo || echo "Seed failed, starting the API anyway."
fi

exec "$@"
