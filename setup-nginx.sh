#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
CONF_SRC="$REPO_DIR/nginx-d31337m3.conf"
CONF_DEST="/etc/nginx/sites-available/d31337m3"
SYMLINK="/etc/nginx/sites-enabled/d31337m3"

if [[ $(id -u) -ne 0 ]]; then
  echo "Error: this script must be run as root. Use sudo ./setup-nginx.sh"
  exit 1
fi

if ! command -v nginx >/dev/null 2>&1; then
  echo "Error: nginx binary not found in PATH. Install system nginx first."
  exit 1
fi

mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled
cp -f "$CONF_SRC" "$CONF_DEST"
rm -f /etc/nginx/sites-enabled/default
ln -sf "$CONF_DEST" "$SYMLINK"

nginx -t
systemctl reload nginx

echo "Nginx reverse proxy configured and reloaded."
