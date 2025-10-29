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

echo "[start.sh] Starting development server on ${HOST}:${PORT}..."
exec "$PYTHON_BIN" manage.py runserver "${HOST}:${PORT}"

