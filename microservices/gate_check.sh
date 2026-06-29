#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "Running microservices health gate..."
"${ROOT_DIR}/microservices/health_check.sh"

echo "Checking orchestrator API root..."
curl -fsS http://127.0.0.1:8006/ >/dev/null

echo "Checking local Nginx API routing..."
curl -fsS -H 'Host: d31337m3.com' http://127.0.0.1/api/health >/dev/null

echo "Gate passed."
