#!/bin/sh
set -e
exec gunicorn forge_api.main:app -c gunicorn.conf.py
