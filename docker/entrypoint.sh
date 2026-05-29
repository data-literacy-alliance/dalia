#!/bin/bash
set -e

echo "Waiting for database..."
while ! python -c "
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()
from django.db import connections
connections['default'].ensure_connection()
" 2>/dev/null; do
    echo "Database unavailable, waiting 1s..."
    sleep 1
done
echo "Database is ready."

# Only web service runs migrations (check if CMD contains "gunicorn")
# Worker service skips to avoid race conditions
# Django does NOT use advisory locks for migration serialization
if echo "$@" | grep -q "gunicorn"; then
    echo "Running migrations..."
    python manage.py migrate --noinput

    echo "Creating superuser if not exists..."
    python manage.py createsuperuser --noinput 2>&1 | grep -v "already exists" || true

    echo "Collecting static files..."
    python manage.py collectstatic --clear --noinput
else
    echo "Skipping migrations (not web service)."
fi

echo "Starting application..."
exec "$@"
