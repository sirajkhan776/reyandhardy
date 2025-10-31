#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
cd "$ROOT"

echo "[build] Installing/migrating DB and seeding if empty…"
python manage.py migrate --noinput

if [[ -f "data.json" ]]; then
  NEED_SEED=$(python - <<'PY'
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','reyhardy.settings')
django.setup()
try:
    from catalog.models import Product
    print('yes' if not Product.objects.exists() else 'no')
except Exception:
    print('yes')
PY
)
  if [[ "$NEED_SEED" == "yes" ]]; then
    echo "[build] Seeding from data.json …"
    python manage.py loaddata data.json || true
  else
    echo "[build] Seed skipped (data present)."
  fi
else
  echo "[build] data.json not found; skipping seed."
fi

echo "[build] Collecting static…"
python manage.py collectstatic --noinput || true

echo "[build] Done."

