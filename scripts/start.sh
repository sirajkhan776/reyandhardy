#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
cd "$ROOT"

echo "[start] Applying migrations…"
python manage.py migrate --noinput

# Seed the database from data.json if present and if app data appears empty
if [[ -f "data.json" ]]; then
  echo "[start] Checking if seeding is required…"
  NEED_SEED=$(python - <<'PY'
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','reyhardy.settings')
django.setup()
try:
    from catalog.models import Product
    need = not Product.objects.exists()
except Exception:
    need = True
print('yes' if need else 'no')
PY
)
  if [[ "$NEED_SEED" == "yes" ]]; then
    echo "[start] Seeding database from data.json …"
    python manage.py loaddata data.json || true
  else
    echo "[start] Seed skipped (data present)."
  fi
else
  echo "[start] data.json not found; skipping seed."
fi

echo "[start] Collecting static files…"
python manage.py collectstatic --noinput || true

echo "[start] Starting server…"
python manage.py runserver 0.0.0.0:${PORT:-8000}

