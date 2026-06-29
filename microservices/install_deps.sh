#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
SERVICES=(client_index payments data_handling auditor watchdog orchestrator)

if [[ ! -d "${VENV_DIR}" ]]; then
  python3 -m venv "${VENV_DIR}"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
pip install --upgrade pip >/dev/null
pip install pyjwt >/dev/null
pip install email-validator >/dev/null

for svc in "${SERVICES[@]}"; do
  req="${ROOT_DIR}/${svc}/requirements.txt"
  if [[ -f "${req}" ]]; then
    echo "Installing deps for ${svc}..."
    pip install -r "${req}" >/dev/null
  fi
done

echo "Dependency installation complete."
