#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
UNIT_DIR="${ROOT_DIR}/systemd"
SYSTEMD_DIR="/etc/systemd/system"

UNITS=(
  d31337m3-auditor.service
  d31337m3-client-index.service
  d31337m3-data-handling.service
  d31337m3-payments.service
  d31337m3-watchdog.service
  d31337m3-orchestrator.service
)

echo "Installing systemd unit files..."
for unit in "${UNITS[@]}"; do
  sudo cp "${UNIT_DIR}/${unit}" "${SYSTEMD_DIR}/${unit}"
done

sudo systemctl daemon-reload

echo "Enabling and starting services..."
for unit in "${UNITS[@]}"; do
  sudo systemctl enable --now "${unit}"
done

echo "Systemd services installed and started."
sudo systemctl --no-pager --full status d31337m3-orchestrator.service | sed -n '1,20p'
