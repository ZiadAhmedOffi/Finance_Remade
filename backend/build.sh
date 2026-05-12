#!/usr/bin/env bash
set -o errexit
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
echo "Running E2E tests..."
python manage.py test funds.test_e2e_deals --keepdb
