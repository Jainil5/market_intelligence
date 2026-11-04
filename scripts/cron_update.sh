#!/usr/bin/env bash
# For Railway Cron or system cron: daily full update after market close (IST).
set -euo pipefail

: "${BASE_URL:?Set BASE_URL e.g. https://your-app.up.railway.app}"
: "${API_KEY:?Set API_KEY}"

curl -fsS -X POST "$BASE_URL/update/stocks" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{"include_fundamentals":true,"include_news":true,"include_announcements":true}' \
  | python -m json.tool
