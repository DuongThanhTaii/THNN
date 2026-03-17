#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT_DIR/scripts/deploy/common.sh"

[[ $# -ge 1 ]] || usage_and_exit
API_BASE_URL="${1%/}"

log "Starting canary deploy for $API_BASE_URL"
prepare_kubeconfig_if_present
run_rollout_command "CANARY_ROLLOUT_COMMAND"
log "Canary deploy command completed"
