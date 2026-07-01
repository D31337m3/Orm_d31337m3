#!/bin/bash
# Startup script for Client Index Service

echo "Starting Client Index Service..."

# Set environment variables (in production, these would come from a secure vault)
export CLIENT_INDEX_JWT_SECRET=${CLIENT_INDEX_JWT_SECRET:-"dev-secret-change-in-production"}
export ORCHESTRATOR_JWT_SECRET=${ORCHESTRATOR_JWT_SECRET:-"dev-secret-change-in-production"}
export JWT_SECRET=${JWT_SECRET:-"dev-secret-change-in-production"}
export JWT_ALGORITHM=${JWT_ALGORITHM:-"HS256"}
export ACCESS_TOKEN_EXPIRE_MINUTES=${ACCESS_TOKEN_EXPIRE_MINUTES:-"1440"}

# Database connection - now using SQLAlchemy with SQLite
# For PostgreSQL production: DATABASE_URL="postgresql://user:password@localhost/d31337m3"
export DATABASE_URL=${DATABASE_URL:-"sqlite:////home/D31337m3/Orm_d31337m3/microservices/state/d31337m3_client_index.db"}

# Infisical secrets manager configuration
export INFISICAL_SITE_URL=${INFISICAL_SITE_URL:-"https://app.infisical.com"}
export INFISICAL_SERVICE_TOKEN=${INFISICAL_SERVICE_TOKEN:-""}
export INFISICAL_ENVIRONMENT=${INFISICAL_ENVIRONMENT:-"prod"}
export INFISICAL_PROJECT_ID=${INFISICAL_PROJECT_ID:-""}
export INFISICAL_SECRETS_PATH=${INFISICAL_SECRETS_PATH:-"/"}

# Service port
export SERVICE_PORT=${SERVICE_PORT:-"8002"}
export PYTHONPATH=${PYTHONPATH:-"/home/D31337m3/Orm_d31337m3/microservices"}

# SQL Debug (set to "true" to see SQL queries)
export SQL_DEBUG=${SQL_DEBUG:-"false"}

# Start the service
echo "Starting Client Index Service on port $SERVICE_PORT"
echo "Using database: $DATABASE_URL"
uvicorn service.main:app --host 0.0.0.0 --port $SERVICE_PORT --reload