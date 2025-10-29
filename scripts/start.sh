#!/usr/bin/env bash
set -euo pipefail

# Run makemigrations, migrate, then start Django's dev server.
# Usage:
#   bash scripts/start.sh              # defaults to 0.0.0.0:8000
#   HOST=127.0.0.1 PORT=8080 bash scripts/start.sh
#   PYTHON=python3 bash scripts/start.sh

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON:-python}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

echo "[start.sh] Applying model changes (makemigrations)..."
"$PYTHON_BIN" manage.py makemigrations --noinput

echo "[start.sh] Migrating database..."
"$PYTHON_BIN" manage.py migrate --noinput

echo "[start.sh] Ensuring an admin superuser exists (one-time)..."
SUPERUSER_USERNAME="${SUPERUSER_USERNAME:-admin}"
SUPERUSER_PASSWORD="${SUPERUSER_PASSWORD:-admin}"
SUPERUSER_EMAIL="${SUPERUSER_EMAIL:-admin@example.com}"
"$PYTHON_BIN" manage.py shell -c "\
from django.contrib.auth import get_user_model;\
import os;\
username=os.environ.get('SUPERUSER_USERNAME','admin');\
password=os.environ.get('SUPERUSER_PASSWORD','admin');\
email=os.environ.get('SUPERUSER_EMAIL','admin@example.com');\
User=get_user_model();\
if not User.objects.filter(username=username).exists():\
    User.objects.create_superuser(username=username, email=email, password=password);\
    print(f'[start.sh] Created superuser {username}');\
else:\
    print(f'[start.sh] Superuser {username} already exists');\
"

echo "[start.sh] Starting development server on ${HOST}:${PORT}..."
exec "$PYTHON_BIN" manage.py runserver "${HOST}:${PORT}"
