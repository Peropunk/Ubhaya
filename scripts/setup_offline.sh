#!/usr/bin/env sh
# UBHAYA offline setup for Linux/macOS (P0.8).
#   While online, once:   scripts/setup_offline.sh --download   (fills vendor/wheels)
#   On any laptop:        scripts/setup_offline.sh              (installs from vendor/wheels if present)
set -eu
cd "$(dirname "$0")/.."
start=$(date +%s)

PY=.venv/bin/python
[ -x "$PY" ] || python3 -m venv .venv

if [ "${1:-}" = "--download" ]; then
  $PY -m pip download -r requirements.txt -d vendor/wheels
  echo "Wheels saved to vendor/wheels. Copy the whole repo folder to the offline laptop."
  exit 0
fi

if [ -d vendor/wheels ]; then
  $PY -m pip install --no-index --find-links vendor/wheels -r requirements.txt
else
  echo "vendor/wheels not found: installing from the internet"
  $PY -m pip install -r requirements.txt
fi

$PY manage.py load-demo
$PY manage.py test
echo "Setup done in $(( ($(date +%s) - start) / 60 )) min. Start with: $PY manage.py run  then open http://127.0.0.1:8000/ui/"
