#!/bin/sh
# Every start: creates the database if missing, applies migrations, then `demo_setup`
# creates missing demo accounts, the Editors group and the sample pages (never changes existing ones).
# The container keeps no files: everything lives in PostgreSQL (DATABASE_URL).
set -e
cd /app/demo
if [ -n "$DATABASE_URL" ]; then python createdb.py; fi
python manage.py migrate --noinput -v 0
python manage.py demo_setup
exec gunicorn demo.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers "${WEB_CONCURRENCY:-2}" --timeout 300 --access-logfile -
