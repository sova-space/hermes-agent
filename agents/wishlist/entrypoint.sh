#!/bin/sh
set -e
alembic upgrade head
exec gunicorn wishlist_api.main:app -c gunicorn.conf.py
