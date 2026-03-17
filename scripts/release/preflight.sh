#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

log() {
  echo "[preflight] $*"
}

log "Running backend lint/type/test gates"
cd "$ROOT_DIR"
uv run ruff format --check
uv run ruff check
uv run ty check
uv run pytest -q

log "Running frontend build/test/perf gates"
cd "$ROOT_DIR/frontend"
npm run test:run
npm run build
npm run perf:budget
npm run a11y
npm run e2e
npm audit --omit=dev

log "Preflight completed successfully"
