#!/bin/sh
set -eu
# Free services have no pre-deploy command. Migrate on each demo startup.
python manage.py check
python manage.py migrate --noinput
exec gunicorn wsgi:application --bind "0.0.0.0:${PORT:-10000}" \
  --workers "${WEB_CONCURRENCY:-1}" --worker-class gthread --threads "${GUNICORN_THREADS:-4}" \
  --timeout 180 --error-logfile -
