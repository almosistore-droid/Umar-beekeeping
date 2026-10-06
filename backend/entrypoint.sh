#!/bin/sh
set -e
# Apply database migrations before starting the API
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-2} \
  --proxy-headers --forwarded-allow-ips='*'
