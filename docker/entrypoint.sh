#!/bin/sh
set -e

should_run_migrations=$(printf '%s' "${RUN_MIGRATIONS_ON_START:-false}" | tr '[:upper:]' '[:lower:]')
STATIC_ROOT=/app/staticfiles
MEDIA_ROOT=/app/media

mkdir -p "$STATIC_ROOT" "$MEDIA_ROOT"

if [ "$(id -u)" = "0" ]; then
    chown -R app:app "$STATIC_ROOT" "$MEDIA_ROOT"
fi

echo "Collecting static files..."
python manage.py collectstatic --noinput

if [ "$(id -u)" = "0" ]; then
    chown -R app:app "$STATIC_ROOT"
fi

if [ "$should_run_migrations" = "true" ]; then
    echo "Applying database migrations..."
    until python manage.py migrate --noinput; do
        echo "Database is unavailable - retrying in 3s"
        sleep 3
    done
fi

echo "Starting gunicorn..."
exec gunicorn Map_of_local_issues.wsgi:application \
    --user app \
    --group app \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout "${GUNICORN_TIMEOUT:-60}" \
    --log-level "${GUNICORN_LOG_LEVEL:-info}"

