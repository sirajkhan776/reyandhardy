#!/usr/bin/env bash
set -euo pipefail

# Export full database contents (app data) to data.json for seeding on Render
# Usage: bash scripts/export_data.sh

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
cd "$ROOT"

echo "[export] Dumping data to data.json …"

# Exclude framework tables that vary by environment
python manage.py dumpdata \
  --exclude contenttypes \
  --exclude auth.permission \
  --exclude admin.logentry \
  --indent 2 > data.json

echo "[export] Done: data.json"

