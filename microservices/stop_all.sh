#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_DIR="${ROOT_DIR}/pids"
SERVICES=(orchestrator watchdog workforce_ops support_hub payments data_handling client_index auditor)

for svc in "${SERVICES[@]}"; do
  pid_file="${PID_DIR}/${svc}.pid"
  if [[ -f "${pid_file}" ]]; then
    pid="$(cat "${pid_file}")"
    if kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" || true
      echo "Stopped ${svc} (${pid})"
    fi
    rm -f "${pid_file}"
  fi
done

echo "Stop sequence complete."
