#!/usr/bin/env bash
set -euo pipefail

SYSTEMD_DIR="/etc/systemd/system"
UNITS=(
  d31337m3-orchestrator.service
  d31337m3-watchdog.service
  d31337m3-workforce-ops.service
  d31337m3-support-hub.service
  d31337m3-payments.service
  d31337m3-data-handling.service
  d31337m3-client-index.service
  d31337m3-auditor.service
)

for unit in "${UNITS[@]}"; do
  sudo systemctl disable --now "${unit}" 2>/dev/null || true
  sudo rm -f "${SYSTEMD_DIR}/${unit}"
done

sudo systemctl daemon-reload
echo "Systemd services removed."
