#!/bin/sh
set -e

exec celery -A app.worker.celery_app:celery_app worker --loglevel=${LOG_LEVEL:-INFO}
