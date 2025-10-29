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

# Ensure Git LFS media are present (no-op if LFS unavailable)
if command -v git >/dev/null 2>&1; then
  if ! command -v git-lfs >/dev/null 2>&1; then
    echo "[start.sh] git-lfs not found; attempting install..."
    if command -v apt-get >/dev/null 2>&1; then
      apt-get update -y >/dev/null 2>&1 || true
      apt-get install -y git-lfs >/dev/null 2>&1 || true
    fi
  fi
  if command -v git-lfs >/dev/null 2>&1; then
    echo "[start.sh] Fetching Git LFS media..."
    git lfs install >/dev/null 2>&1 || true
    git lfs pull || true
  else
    echo "[start.sh] Git LFS still unavailable; videos may not load (pointer files)."
  fi
fi

echo "[start.sh] Applying model changes (makemigrations)..."
"$PYTHON_BIN" manage.py makemigrations --noinput

echo "[start.sh] Migrating database..."
"$PYTHON_BIN" manage.py migrate --noinput

echo "[start.sh] Ensuring an admin superuser exists (one-time)..."
SUPERUSER_USERNAME="${SUPERUSER_USERNAME:-admin}"
SUPERUSER_PASSWORD="${SUPERUSER_PASSWORD:-admin}"
SUPERUSER_EMAIL="${SUPERUSER_EMAIL:-admin@example.com}"
SUPERUSER_USERNAME="$SUPERUSER_USERNAME" \
SUPERUSER_PASSWORD="$SUPERUSER_PASSWORD" \
SUPERUSER_EMAIL="$SUPERUSER_EMAIL" \
"$PYTHON_BIN" manage.py shell << 'PY'
from django.contrib.auth import get_user_model
import os

username = os.environ.get('SUPERUSER_USERNAME', 'admin')
password = os.environ.get('SUPERUSER_PASSWORD', 'admin')
email = os.environ.get('SUPERUSER_EMAIL', 'admin@example.com')

User = get_user_model()
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"[start.sh] Created superuser {username}")
else:
    print(f"[start.sh] Superuser {username} already exists")
PY

# Seed initial data (idempotent)
SEED_DEMO="${SEED_DEMO:-true}"
echo "[start.sh] Seeding base store data (seed_store)..."
"$PYTHON_BIN" manage.py seed_store || echo "[start.sh] seed_store failed or not available"

if [ "$SEED_DEMO" = "true" ] || [ "$SEED_DEMO" = "1" ]; then
  echo "[start.sh] Seeding demo data (seed_demo)..."
  "$PYTHON_BIN" manage.py seed_demo || echo "[start.sh] seed_demo failed or not available"
else
  echo "[start.sh] Skipping demo data seeding (SEED_DEMO=$SEED_DEMO)"
fi

echo "[start.sh] Starting development server on ${HOST}:${PORT}..."
exec "$PYTHON_BIN" manage.py runserver "${HOST}:${PORT}"
