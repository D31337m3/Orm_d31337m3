# Orm_d31337m3

Full-stack privacy and reputation management platform with:

- React frontend (`frontend/`)
- API microservices stack (`microservices/`)
- Nginx edge routing (`nginx-d31337m3.conf` + `setup-nginx.sh`)

## Current State (2026-06-30)

### Product and UI

- Updated production branding pipeline with source assets in `brand_assets/` and active runtime assets in `frontend/public/`.
- `BrandMark` now renders official square + horizontal logo assets consistently across login, registration, dashboard, and shared banners.
- Broker submission dialog added to both public landing and authenticated dashboard surfaces.
- Broker submission supports:
	- single-entry structured form
	- CSV upload with parser + header aliasing
	- row-level validation and preview
	- downloadable CSV template
	- support ticket submission (authenticated) and secure support mail intake fallback (public)
- Landing page right-side telemetry card now includes `service.health (public)` directly under `live.feed` using matching visual format.

### Security Emphasis

- Public service health intentionally exposes only safe status + latency summaries.
- Sensitive diagnostics are explicitly redacted from public UI surfaces.
- Service-tier authentication uses JWT verification in shared middleware.
- Secrets are loaded Infisical-first with environment fallback (`microservices/shared/secrets_manager.py`).
- Security posture documentation is maintained in `docs/security_and_privacy.md`.

## Current Implementation

API services are organized as microservices:

- `client_index` (`8002`)
- `payments` (`8003`)
- `data_handling` (`8004`)
- `auditor` (`8005`)
- `orchestrator` (`8006`)
- `watchdog` (`8007`)

Nginx routes `/api/*` to `orchestrator` on `127.0.0.1:8006`.

Additional operational services:

- `support_hub` (`8008`)
- `workforce_ops` (`8009`)

## Local Development

### Frontend

```bash
cd frontend
npm install
npm start
```

### Microservices

```bash
cd microservices
./install_deps.sh
./start_all.sh
./health_check.sh
```

Stop microservices:

```bash
cd microservices
./stop_all.sh
```

## Production Operations

Install and enable systemd services:

```bash
cd microservices
./systemd/install_systemd_services.sh
```

Run the deployment gate:

```bash
cd microservices
./gate_check.sh
```

Rollback command pack:

```bash
cd microservices
./rollback.sh
```

## Nginx

Apply repository nginx config:

```bash
sudo ./setup-nginx.sh
```

Inspect active nginx config:

```bash
sudo nginx -T
```

## Documentation

- [Documentation Index](docs/README.md)
- [Release Note: 2026-06-30](docs/release_note_2026-06-30.md)
- [Agent Go-Live Guide](docs/agent_go_live_microservices.md)
- [Go-Live Quick Runbook](docs/go_live_quick_runbook.md)
- [Security and Privacy](docs/security_and_privacy.md)
- [Roadmap](docs/roadmap.md)
- [Future Development](docs/future_development.md)
- [Microservices Operations](microservices/README.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
