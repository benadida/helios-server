#!/usr/bin/env bash

set -o errexit
set -o pipefail

cmd="$@"

postgres_ready() {
    python << END
import sys
import psycopg2

try:
    psycopg2.connect(
        dbname="${POSTGRES_DB}",
        user="${POSTGRES_USER}",
        password="${POSTGRES_PASSWORD}",
        host="${POSTGRES_HOST}",
        port="${POSTGRES_PORT}")
except psycopg2.OperationalError:
    sys.exit(-1)

sys.exit(0)
END
}

counter=0
until postgres_ready; do
  >&2 echo 'PostgreSQL is unavailable (sleeping)...'
  sleep 1
  if [ $counter -gt "60" ]; then
    echo "Can't connect to PostgreSQL. Exiting."
    exit 1
  fi
  counter=$(expr $counter + 1)
done

>&2 echo 'PostgreSQL is up - continuing...'


case "$cmd" in
    migrate)
        python manage.py migrate --noinput
    ;;
    collectstatic)
        python manage.py collectstatic --clear --no-input
    ;;
    *)
        $cmd  # usage start.sh or gunicorn.sh
    ;;
esac
