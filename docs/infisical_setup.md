# Infisical Secrets Management Setup

This guide explains how to set up Infisical for managing JWT secrets and other sensitive configuration across all microservices.

## Overview

The application uses **Infisical** (https://infisical.com) for centralized secrets management. All JWT tokens and sensitive configuration are retrieved from Infisical at runtime instead of being stored in environment files or code.

## Architecture

```
┌─────────────────────────────────────┐
│  Infisical Vault (Cloud/Self-Hosted) │
│  - JWT Secrets                      │
│  - Database Credentials             │
│  - API Keys                         │
└──────────────┬──────────────────────┘
               │ INFISICAL_SERVICE_TOKEN
               ▼
┌──────────────────────────────────────┐
│  Microservices (systemd services)    │
│  - client_index (8002)               │
│  - payments (8003)                   │
│  - data_handling (8004)              │
│  - auditor (8005)                    │
│  - orchestrator (8006)               │
│  - watchdog (8007)                   │
└──────────────────────────────────────┘
```

## Setup Steps

### 1. Create Infisical Account

1. Go to https://app.infisical.com
2. Sign up for a free account
3. Create a new organization

### 2. Create Infisical Project

1. In your organization, create a new project named `d31337m3`
2. Create two environments:
   - `dev` - for development
   - `prod` - for production

### 3. Add JWT Secrets to Infisical

For each service, add the following secrets in both `dev` and `prod` environments:

#### Client Index Service (`/client_index` path)
- `CLIENT_INDEX_JWT_SECRET`: A random 32+ character string (e.g., `$(openssl rand -base64 32)`)
- `DATABASE_URL`: `sqlite:////tmp/d31337m3_client_index.db` (or PostgreSQL URL for production)

#### Payments Service (`/payments` path)
- `PAYMENTS_JWT_SECRET`: A random 32+ character string
- `DATABASE_URL`: `sqlite:////tmp/d31337m3_payments.db` (or PostgreSQL URL)

#### Data Handling Service (`/data_handling` path)
- `DATA_HANDLING_JWT_SECRET`: A random 32+ character string
- `DATABASE_URL`: `sqlite:////tmp/d31337m3_data_handling.db` (or PostgreSQL URL)

#### Auditor Service (`/auditor` path)
- `AUDITOR_JWT_SECRET`: A random 32+ character string
- `DATABASE_URL`: `sqlite:////tmp/d31337m3_auditor.db` (or PostgreSQL URL)

#### Watchdog Service (`/watchdog` path)
- `WATCHDOG_JWT_SECRET`: A random 32+ character string

#### Orchestrator Service (`/orchestrator` path)
- `ORCHESTRATOR_JWT_SECRET`: A random 32+ character string

#### Shared Secrets (`/` root path)
- `JWT_SECRET`: A random 32+ character string (legacy/fallback)
- `JWT_ALGORITHM`: `HS256`
- `ACCESS_TOKEN_EXPIRE_MINUTES`: `1440` (24 hours)

### 4. Generate Service Token

1. In Infisical, navigate to **Project Settings → Service Tokens**
2. Create a new service token for your project
3. Copy the token (this is `INFISICAL_SERVICE_TOKEN`)

### 5. Configure System Environment

On your production server, set the following environment variables:

```bash
export INFISICAL_SITE_URL="https://app.infisical.com"  # or your self-hosted URL
export INFISICAL_SERVICE_TOKEN="<your_service_token>"
export INFISICAL_ENVIRONMENT="prod"  # or "dev"
export INFISICAL_PROJECT_ID="<your_project_id>"
```

You can set these in:
- `/etc/environment` (system-wide)
- `/home/D31337m3/.bashrc` (user-specific)
- Or directly in systemd service files (already configured)

### 6. Reload systemd Services

After configuring Infisical, reload the systemd daemon and restart services:

```bash
sudo systemctl daemon-reload
sudo systemctl restart d31337m3-client-index.service
sudo systemctl restart d31337m3-payments.service
sudo systemctl restart d31337m3-data-handling.service
sudo systemctl restart d31337m3-auditor.service
sudo systemctl restart d31337m3-orchestrator.service
sudo systemctl restart d31337m3-watchdog.service
```

### 7. Verify Integration

Check that services are successfully loading secrets from Infisical:

```bash
# Check service logs for Infisical initialization
journalctl -u d31337m3-client-index -n 20

# Should see: "Infisical initialized successfully. Loaded X secrets..."
```

## Development Setup (Optional)

For local development without Infisical, the services fall back to environment variables:

```bash
# Set these in your shell or .env file
export CLIENT_INDEX_JWT_SECRET="dev-secret-change-in-production"
export PAYMENTS_JWT_SECRET="dev-secret-change-in-production"
export DATA_HANDLING_JWT_SECRET="dev-secret-change-in-production"
export AUDITOR_JWT_SECRET="dev-secret-change-in-production"
export WATCHDOG_JWT_SECRET="dev-secret-change-in-production"
export ORCHESTRATOR_JWT_SECRET="dev-secret-change-in-production"
export JWT_SECRET="dev-secret-change-in-production"
export JWT_ALGORITHM="HS256"
export ACCESS_TOKEN_EXPIRE_MINUTES="1440"
export DATABASE_URL="sqlite:////tmp/d31337m3_client_index.db"
```

## Self-Hosted Infisical (Optional)

If you prefer to self-host Infisical:

1. Deploy Infisical using Docker or their deployment guides: https://infisical.com/docs
2. Update `INFISICAL_SITE_URL` to point to your self-hosted instance
3. Generate a service token from your self-hosted instance
4. Follow the same setup steps above

## Security Best Practices

1. **Never commit secrets to Git** - All secrets are managed in Infisical
2. **Rotate secrets regularly** - Update JWT secrets every 90 days
3. **Use strong tokens** - Service tokens should be 32+ characters
4. **Limit token scope** - Service tokens should have minimal required permissions
5. **Enable audit logging** - Monitor who accesses secrets in Infisical
6. **Separate environments** - Keep dev and prod secrets isolated
7. **Use HTTPS only** - Ensure `INFISICAL_SITE_URL` is HTTPS

## Troubleshooting

### Secrets not loading?

Check the service logs:
```bash
journalctl -u d31337m3-client-index -n 50 --no-pager
```

Look for:
- "Infisical initialized successfully" - confirms successful connection
- "No Infisical credentials configured" - missing `INFISICAL_SERVICE_TOKEN`
- "Failed to initialize Infisical" - check token, project ID, environment

### Invalid token errors?

1. Verify `INFISICAL_SERVICE_TOKEN` is correct
2. Check that the token hasn't expired
3. Ensure the token has permissions for the project

### Secrets path issues?

By default, secrets are loaded from `/` (root). To use service-specific paths:
- Set `INFISICAL_SECRETS_PATH` environment variable
- Example: `/client_index` to load from `/client_index` path in Infisical

## JWT Token Flow

```
1. Service starts → init_infisical() called
2. Infisical client fetches secrets using INFISICAL_SERVICE_TOKEN
3. JWT secrets cached in memory
4. When creating tokens:
   - User token: Uses service-specific JWT secret (e.g., CLIENT_INDEX_JWT_SECRET)
   - Service token: Uses corresponding SERVICE_JWT_SECRET
5. When verifying tokens:
   - Tries all service secrets + legacy secret for compatibility
```

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `INFISICAL_SITE_URL` | `https://app.infisical.com` | Infisical instance URL |
| `INFISICAL_SERVICE_TOKEN` | `` | Service token for authentication |
| `INFISICAL_CLIENT_ID` | `` | OAuth client ID (alternative to service token) |
| `INFISICAL_CLIENT_SECRET` | `` | OAuth client secret (alternative to service token) |
| `INFISICAL_PROJECT_ID` | `` | Project ID in Infisical |
| `INFISICAL_ENVIRONMENT` | `prod` | Environment: `dev`, `staging`, `prod` |
| `INFISICAL_SECRETS_PATH` | `/` | Path prefix for secrets in Infisical |

## Next Steps

1. Create Infisical account and project
2. Add all required secrets
3. Generate service token
4. Configure server environment variables
5. Reload systemd and restart services
6. Verify logs show successful Infisical initialization
