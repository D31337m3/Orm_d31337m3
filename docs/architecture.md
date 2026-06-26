# Architecture

This document describes the high-level architecture of Orm_d31337m3.

## Components

- Frontend (React): serves the single-page app; development server runs on port 3000. The production build places static assets under `frontend/build/static`.
- Backend (FastAPI): REST API and business logic; runs on port 8001 in development. Entry point: `backend/server.py`.
- Reverse proxy (Nginx): centralizes HTTP(S) ingress and routes `/api/` to backend and `/*` to frontend.

## Request Flow

1. Client (browser) requests `https://d31337m3.com`.
2. Nginx handles TLS termination and routes requests:
   - Requests under `/api/` are proxied to `127.0.0.1:8001`.
   - All other requests are proxied to `127.0.0.1:3000` (or served statically).
3. Backend interacts with persistent storage (configure DB externally) and other services.

## Deployment Notes

- In production, build the frontend with `npm run build` and serve static files either via Nginx or a CDN for better performance.
- The backend should run as a systemd service or under a process manager (e.g., `gunicorn`/`uvicorn` with `systemd` or `pm2` for Node-based servers).
- Use environment variables for configuration (DB URLs, secret keys, API keys).

## Scaling
 (Todo:)
- Use a load balancer in front of multiple app instances for high availability.
- Offload static assets to a CDN.
- Use connection pooling for database access and horizontal scaling for stateless backend components.

## Observability
 (Todo:)
- Add structured logging, metrics (Prometheus), and tracing (OpenTelemetry) to critical services.
- Centralize logs and set up alerting for errors and operational thresholds.
