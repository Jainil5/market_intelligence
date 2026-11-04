#!/usr/bin/env bash
# Local bootstrap: venv, dependencies, .env template, setup verification.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VENV="$ROOT/.venv"
if [[ ! -d "$VENV" ]]; then
  if [[ -d "$ROOT/venv" ]]; then
    VENV="$ROOT/venv"
  else
    echo "Creating .venv ..."
    python3 -m venv "$VENV"
  fi
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"
python -m pip install --upgrade pip -q
pip install -r requirements.txt -r requirements-dev.txt -q

if [[ ! -f "$ROOT/.env" ]]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "Created .env from .env.example — edit Supabase keys and API_KEY before production use."
fi

echo ""
echo "Supabase (run in SQL Editor, in order):"
echo "  1. database/schema.sql"
echo "  2. database/migrations/001_bse_scrip_code.sql"
echo "  3. database/seed.sql"
echo "  4. database/read_policies.sql (optional)"
echo "  5. database/storage_setup.sql (optional bucket)"
echo ""
python "$ROOT/scripts/verify_setup.py"
