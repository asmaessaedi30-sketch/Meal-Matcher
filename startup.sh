#!/usr/bin/env bash
set -euo pipefail

exec gunicorn \
  --chdir meal_matcher \
  --bind 0.0.0.0:8000 \
  --workers 1 \
  --threads 4 \
  --timeout 600 \
  --access-logfile - \
  --error-logfile - \
  app:app
