#!/bin/bash
# Startup script for Watchdog Service

echo "Starting Watchdog Service..."

# Set environment variables (in production, these would come from a secure vault)
export WATCHDOG_JWT_SECRET=${WATCHDOG_JWT_SECRET:-"dev-secret-change-in-production"}
export CLIENT_INDEX_JWT_SECRET=${CLIENT_INDEX_JWT_SECRET:-"dev-secret-change-in-production"}
export JWT_SECRET=${JWT_SECRET:-"dev-secret-change-in-production"}
export JWT_ALGORITHM=${JWT_ALGORITHM:-"HS256"}
export ACCESS_TOKEN_EXPIRE_MINUTES=${ACCESS_TOKEN_EXPIRE_MINUTES:-"1440"}

# Infisical secrets manager configuration
export INFISICAL_SITE_URL=${INFISICAL_SITE_URL:-"https://app.infisical.com"}
export INFISICAL_SERVICE_TOKEN=${INFISICAL_SERVICE_TOKEN:-""}
export INFISICAL_ENVIRONMENT=${INFISICAL_ENVIRONMENT:-"prod"}
export INFISICAL_PROJECT_ID=${INFISICAL_PROJECT_ID:-""}
export INFISICAL_SECRETS_PATH=${INFISICAL_SECRETS_PATH:-"/"}

# Service port
export SERVICE_PORT=${SERVICE_PORT:-"8007"}
export PYTHONPATH=${PYTHONPATH:-"/home/D31337m3/Orm_d31337m3/microservices"}

# Start the service
echo "Starting Watchdog Service on port $SERVICE_PORT"
uvicorn service.main:app --host 0.0.0.0 --port $SERVICE_PORT --reload