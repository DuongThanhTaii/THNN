#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <base_url>"
  echo "Example: $0 https://api.example.com"
  exit 1
fi

BASE_URL="${1%/}"

log() {
  echo "[smoke] $*"
}

check_http() {
  local url="$1"
  local expected="${2:-200}"
  local code
  code="$(curl -sS -o /tmp/smoke.out -w "%{http_code}" "$url")"
  if [[ "$code" != "$expected" ]]; then
    echo "Smoke check failed for $url (got $code expected $expected)"
    cat /tmp/smoke.out
    exit 1
  fi
}

log "Checking system status"
check_http "$BASE_URL/api/v1/system/status" 200

log "Checking metrics endpoint"
check_http "$BASE_URL/api/v1/system/metrics" 200

log "Running backend webhook integration smoke tests"
cd "$(cd "$(dirname "$0")/../.." && pwd)"
uv run pytest -q tests/integrations/test_webhook_flows.py

log "Post-deploy smoke completed successfully"
