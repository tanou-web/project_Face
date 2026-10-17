#!/usr/bin/env bash
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

if [ -f "manage.py" ]; then
    python manage.py collectstatic --noinput
    python manage.py migrate
elif [ -f "photo/manage.py" ]; then
    python photo/manage.py collectstatic --noinput
    python photo/manage.py migrate
fi
