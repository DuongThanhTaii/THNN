#!/usr/bin/env bash
set -euo pipefail

log() {
  echo "[deploy] $*"
}

usage_and_exit() {
  echo "Usage: $0 <api_base_url>"
  echo "Example: $0 https://staging-api.example.com"
  exit 1
}

require_var() {
  local name="$1"
  local value="${!name:-}"
  if [[ -z "$value" ]]; then
    echo "Missing required variable: $name"
    exit 1
  fi
}

run_rollout_command() {
  local command_var="$1"
  local command_value="${!command_var:-}"

  if [[ -z "$command_value" ]]; then
    echo "Missing rollout command variable: $command_var"
    echo "Set it in GitHub Environment Variables for this environment."
    exit 1
  fi

  log "Executing rollout command from $command_var"
  bash -lc "$command_value"
}

prepare_kubeconfig_if_present() {
  local kube_b64="${KUBE_CONFIG_B64:-}"
  if [[ -z "$kube_b64" ]]; then
    return
  fi

  local kube_tmp
  kube_tmp="$(mktemp)"
  echo "$kube_b64" | base64 -d > "$kube_tmp"
  export KUBECONFIG="$kube_tmp"
  log "KUBECONFIG prepared from KUBE_CONFIG_B64"
}
