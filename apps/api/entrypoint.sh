#!/bin/sh
set -eu
if [ "${ENABLE_HISTORY:-false}" = "true" ]; then
  case "${DATABASE_URL:-}" in
    postgresql*) alembic upgrade head ;;
  esac
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log --workers 1
