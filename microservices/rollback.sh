#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "Stopping microservices managed by scripts..."
"${ROOT_DIR}/microservices/stop_all.sh" || true

echo "Stopping systemd microservices if installed..."
for unit in d31337m3-orchestrator.service d31337m3-watchdog.service d31337m3-payments.service d31337m3-data-handling.service d31337m3-client-index.service d31337m3-auditor.service; do
  sudo systemctl stop "$unit" 2>/dev/null || true
done

echo "Restoring legacy API upstream (8001) in active Nginx site..."
for site in /etc/nginx/sites-available/d31337m3.com /etc/nginx/sites-available/d31337m3; do
  if [[ -f "$site" ]]; then
    sudo sed -i 's|proxy_pass http://127.0.0.1:8006/api/;|proxy_pass http://127.0.0.1:8001/api/;|g' "$site"
  fi
done
sudo nginx -t
sudo systemctl reload nginx

echo "Starting legacy backend on 8001..."
if [[ -d "${ROOT_DIR}/backend/venv" ]]; then
  (
    cd "${ROOT_DIR}/backend"
    source venv/bin/activate
    nohup uvicorn server:app --host 127.0.0.1 --port 8001 >/tmp/d31337m3-legacy-backend.log 2>&1 &
  )
fi

echo "Rollback commands completed. Validate with:"
echo "curl -I -H 'Host: d31337m3.com' http://127.0.0.1/"
