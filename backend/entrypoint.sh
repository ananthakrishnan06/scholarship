#!/bin/sh
set -eu
python backend/manage.py migrate --noinput
python backend/manage.py seed_scholarships
python backend/manage.py collectstatic --noinput
exec gunicorn --chdir backend config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers "${GUNICORN_WORKERS:-1}" --threads "${GUNICORN_THREADS:-2}" --timeout 180 --access-logfile -
