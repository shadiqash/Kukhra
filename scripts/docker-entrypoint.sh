#!/bin/sh
# Runs before the container's main command. Celery containers reuse this
# entrypoint but skip migrate/collectstatic by setting SKIP_DJANGO_SETUP=1.
set -e

if [ "${SKIP_DJANGO_SETUP:-0}" != "1" ]; then
    echo "Applying database migrations..."
    python manage.py migrate --noinput
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
fi

exec "$@"
