#!/usr/bin/env bash
set -euo pipefail

# Configure Mailcow sender-dependent relayhost for a mailbox.
#
# Example:
#   RELAY_HOST=smtp.your-azure-relay.net \
#   RELAY_PORT=587 \
#   RELAY_USERNAME='smtp-user' \
#   RELAY_PASSWORD='super-secret' \
#   MAILBOX='support@d31337m3.com' \
#   bash scripts/configure_mailcow_relayhost.sh

MAILBOX="${MAILBOX:-support@d31337m3.com}"
RELAY_HOST="${RELAY_HOST:-}"
RELAY_PORT="${RELAY_PORT:-2525}"
RELAY_USERNAME="${RELAY_USERNAME:-}"
RELAY_PASSWORD="${RELAY_PASSWORD:-}"
MAILCOW_CONF="${MAILCOW_CONF:-/opt/mailcow-dockerized/mailcow.conf}"
MYSQL_CONTAINER="${MYSQL_CONTAINER:-mailcowdockerized-mysql-mailcow-1}"
POSTFIX_CONTAINER="${POSTFIX_CONTAINER:-mailcowdockerized-postfix-mailcow-1}"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

need_cmd sudo
need_cmd docker
need_cmd timeout
need_cmd bash

if [[ -z "$RELAY_HOST" ]]; then
  RELAY_HOST="$(ip route show default 2>/dev/null | awk 'NR==1 {print $3}')"
fi

if [[ -z "$RELAY_HOST" ]]; then
  echo "Missing relay host and could not auto-detect host gateway" >&2
  exit 1
fi

if [[ ! "$RELAY_PORT" =~ ^[0-9]+$ ]]; then
  echo "RELAY_PORT must be numeric" >&2
  exit 1
fi

if [[ ! -f "$MAILCOW_CONF" ]]; then
  echo "Mailcow config not found: $MAILCOW_CONF" >&2
  exit 1
fi

DBROOT="$(sudo grep '^DBROOT=' "$MAILCOW_CONF" | cut -d= -f2-)"
if [[ -z "$DBROOT" ]]; then
  echo "Could not read DBROOT from $MAILCOW_CONF" >&2
  exit 1
fi

MAILBOX_DOMAIN="${MAILBOX#*@}"
NEXTHOP="[${RELAY_HOST}]:${RELAY_PORT}"

echo "Testing TCP connectivity to relay ${RELAY_HOST}:${RELAY_PORT}..."
if timeout 8 bash -lc "cat < /dev/null > /dev/tcp/${RELAY_HOST}/${RELAY_PORT}"; then
  echo "OK: relay endpoint is reachable"
else
  echo "WARN: relay endpoint is not reachable from this host. Continuing anyway." >&2
fi

echo "Validating mailbox exists in Mailcow: ${MAILBOX}"
MAILBOX_COUNT="$(sudo docker exec "$MYSQL_CONTAINER" mysql -N -B -uroot -p"$DBROOT" -D mailcow \
  -e "SELECT COUNT(*) FROM mailbox WHERE username='${MAILBOX}';")"
if [[ "$MAILBOX_COUNT" != "1" ]]; then
  echo "Mailbox not found in Mailcow: ${MAILBOX}" >&2
  exit 1
fi

echo "Upserting relayhost entry: ${NEXTHOP}"
sudo docker exec "$MYSQL_CONTAINER" mysql -N -B -uroot -p"$DBROOT" -D mailcow -e "
INSERT INTO relayhosts (hostname, username, password, active)
VALUES ('${NEXTHOP}', '${RELAY_USERNAME}', '${RELAY_PASSWORD}', 1)
ON DUPLICATE KEY UPDATE
  username=VALUES(username),
  password=VALUES(password),
  active=1;
"

RELAY_ID="$(sudo docker exec "$MYSQL_CONTAINER" mysql -N -B -uroot -p"$DBROOT" -D mailcow \
  -e "SELECT id FROM relayhosts WHERE hostname='${NEXTHOP}' LIMIT 1;")"

if [[ -z "$RELAY_ID" ]]; then
  echo "Failed to resolve relayhost id for ${NEXTHOP}" >&2
  exit 1
fi

echo "Binding mailbox ${MAILBOX} to relayhost id=${RELAY_ID}"
sudo docker exec "$MYSQL_CONTAINER" mysql -N -B -uroot -p"$DBROOT" -D mailcow -e "
UPDATE mailbox
SET attributes = JSON_SET(attributes, '$.relayhost', '${RELAY_ID}')
WHERE username='${MAILBOX}';
"

echo "(Optional) Also bind domain ${MAILBOX_DOMAIN} to relayhost id=${RELAY_ID}"
if [[ "${APPLY_TO_DOMAIN:-false}" == "true" ]]; then
  sudo docker exec "$MYSQL_CONTAINER" mysql -N -B -uroot -p"$DBROOT" -D mailcow -e "
  UPDATE domain SET relayhost='${RELAY_ID}' WHERE domain='${MAILBOX_DOMAIN}';
  "
  echo "Domain relayhost updated for ${MAILBOX_DOMAIN}"
fi

echo "Reloading postfix and flushing queue"
sudo docker exec "$POSTFIX_CONTAINER" postfix reload
sudo docker exec "$POSTFIX_CONTAINER" postqueue -f

echo "Current mailbox relayhost value:"
sudo docker exec "$MYSQL_CONTAINER" mysql -N -B -uroot -p"$DBROOT" -D mailcow \
  -e "SELECT username, JSON_UNQUOTE(JSON_EXTRACT(attributes, '$.relayhost')) FROM mailbox WHERE username='${MAILBOX}';"

echo "Done. Monitor delivery logs with:"
echo "  sudo docker logs -f ${POSTFIX_CONTAINER} | grep -Ei 'status=|relay=|dsn='"
