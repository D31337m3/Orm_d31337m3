#!/usr/bin/env bash
set -euo pipefail

# Emergency recovery for microservices managed by systemd.
# - Stops all services
# - Clears stale listeners on known ports
# - Resets failed unit state
# - Starts services in runbook order
# - Verifies systemd state and /health endpoints

SERVICES=(
  "d31337m3-auditor"
  "d31337m3-client-index"
  "d31337m3-data-handling"
  "d31337m3-payments"
  "d31337m3-watchdog"
  "d31337m3-orchestrator"
)

declare -A PORT_MAP=(
  ["d31337m3-client-index"]=8002
  ["d31337m3-payments"]=8003
  ["d31337m3-data-handling"]=8004
  ["d31337m3-auditor"]=8005
  ["d31337m3-orchestrator"]=8006
  ["d31337m3-watchdog"]=8007
)

MAX_HEALTH_RETRIES="${MAX_HEALTH_RETRIES:-25}"
HEALTH_RETRY_SLEEP="${HEALTH_RETRY_SLEEP:-1}"

log() {
  printf "[%s] %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

as_root() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

get_listener_pids_for_port() {
  local port="$1"
  as_root ss -ltnp | awk -v needle=":${port}" '
    $4 ~ needle "$" {
      if (match($0, /pid=[0-9]+/)) {
        print substr($0, RSTART + 4, RLENGTH - 4)
      }
    }
  ' | sort -u
}

kill_stale_port_listener() {
  local port="$1"
  local pids
  pids="$(get_listener_pids_for_port "$port" || true)"

  if [[ -z "${pids}" ]]; then
    return 0
  fi

  log "Port ${port} has stale listener pid(s): ${pids}"

  while IFS= read -r pid; do
    [[ -z "${pid}" ]] && continue
    as_root kill -TERM "${pid}" || true
  done <<< "${pids}"

  sleep 1

  pids="$(get_listener_pids_for_port "$port" || true)"
  if [[ -n "${pids}" ]]; then
    while IFS= read -r pid; do
      [[ -z "${pid}" ]] && continue
      as_root kill -KILL "${pid}" || true
    done <<< "${pids}"
  fi
}

check_service_states() {
  local failed=0
  for svc in "${SERVICES[@]}"; do
    local state
    state="$(systemctl is-active "${svc}" || true)"
    if [[ "${state}" != "active" ]]; then
      log "Service not active: ${svc} (${state})"
      failed=1
    fi
  done
  return "${failed}"
}

check_health_endpoints() {
  local failed=0
  for svc in "${SERVICES[@]}"; do
    local port="${PORT_MAP[${svc}]:-}"
    [[ -z "${port}" ]] && continue

    local ok=0
    local i
    for ((i=1; i<=MAX_HEALTH_RETRIES; i++)); do
      if curl -fsS --max-time 2 "http://127.0.0.1:${port}/health" >/dev/null 2>&1; then
        ok=1
        break
      fi
      sleep "${HEALTH_RETRY_SLEEP}"
    done

    if [[ "${ok}" -eq 1 ]]; then
      log "Health OK: ${svc} (:${port})"
    else
      log "Health FAILED: ${svc} (:${port})"
      failed=1
    fi
  done

  return "${failed}"
}

print_failure_logs() {
  for svc in "${SERVICES[@]}"; do
    local state
    state="$(systemctl is-active "${svc}" || true)"
    if [[ "${state}" != "active" ]]; then
      log "Recent logs for failed service ${svc}:"
      as_root journalctl -u "${svc}" -n 50 --no-pager || true
    fi
  done
}

main() {
  log "Starting instant recovery run"

  log "Stopping services"
  as_root systemctl stop "${SERVICES[@]}" || true

  log "Clearing stale listeners on ports 8002-8007"
  local ports=(8002 8003 8004 8005 8006 8007)
  for p in "${ports[@]}"; do
    kill_stale_port_listener "${p}"
  done

  log "Resetting failed systemd state"
  as_root systemctl reset-failed || true

  log "Starting services in runbook order"
  as_root systemctl start "${SERVICES[@]}"

  log "Validating service active state"
  if ! check_service_states; then
    print_failure_logs
    exit 1
  fi

  log "Validating /health endpoints"
  if ! check_health_endpoints; then
    print_failure_logs
    exit 1
  fi

  log "Recovery completed successfully"
}

main "$@"
