#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
cd "$ROOT"

echo "[build] Installing dependencies…"
python -m pip install --upgrade pip wheel setuptools
python -m pip install -r requirements.txt

echo "[build] Migrating DB and seeding if empty…"
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
    # Remove default Site to avoid unique domain conflicts during loaddata
    python - <<'PY'
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','reyhardy.settings')
django.setup()
try:
    from django.contrib.sites.models import Site
    Site.objects.all().delete()
    print('[build] Cleared default Site')
except Exception as e:
    print('[build] Site cleanup skipped:', e)
PY
    python manage.py loaddata data.json --verbosity 2 || true
  else
    echo "[build] Seed skipped (data present)."
  fi
else
  echo "[build] data.json not found; skipping seed."
fi

echo "[build] Collecting static…"
python manage.py collectstatic --noinput || true

echo "[build] Done."
