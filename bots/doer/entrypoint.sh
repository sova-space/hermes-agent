#!/bin/sh
set -e
exec gunicorn doer_api.main:app -c gunicorn.conf.py
