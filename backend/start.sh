#!/usr/bin/env bash
set -o errexit

python manage.py migrate --noinput
python manage.py collectstatic --noinput
exec gunicorn --bind 0.0.0.0:${PORT:-8080} backend_app.wsgi:application
