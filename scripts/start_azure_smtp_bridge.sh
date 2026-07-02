#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/home/D31337m3/Orm_d31337m3"
VENV_PY="${ROOT_DIR}/microservices/.venv/bin/python"
LIVE_ENV_FILE="/etc/d31337m3/client-index.infisical.env"
ENV_FILE="${ROOT_DIR}/.env.infisical.runtime"

if [[ ! -x "$VENV_PY" ]]; then
  echo "Missing microservices virtualenv at $VENV_PY" >&2
  exit 1
fi

if [[ -n "${INFISICAL_SERVICE_TOKEN:-}" && -n "${INFISICAL_PROJECT_ID:-}" ]]; then
  :
elif [[ -f "$LIVE_ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$LIVE_ENV_FILE"
  set +a
elif [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

export PYTHONPATH="${ROOT_DIR}/microservices:${PYTHONPATH:-}"
export AZURE_SMTP_BRIDGE_HOST="${AZURE_SMTP_BRIDGE_HOST:-0.0.0.0}"
export AZURE_SMTP_BRIDGE_PORT="${AZURE_SMTP_BRIDGE_PORT:-2525}"

exec "$VENV_PY" "${ROOT_DIR}/scripts/azure_smtp_bridge.py"