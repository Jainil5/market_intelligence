#!/usr/bin/env bash
# Smoke test against a running API. Defaults: http://127.0.0.1:8000
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
API_KEY="${API_KEY:?Set API_KEY in .env or environment}"

echo "Health ..."
curl -fsS "$BASE_URL/health" | python -m json.tool

echo "List stocks ..."
curl -fsS "$BASE_URL/stocks" -H "x-api-key: $API_KEY" | python -m json.tool

echo "Incremental price update (STK001) ..."
curl -fsS -X POST "$BASE_URL/update/prices" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{"stock_id":"STK001","include_fundamentals":true}' | python -m json.tool

echo "Smoke test completed."
