# Microservices Operations

This directory contains the backend microservices and production-oriented startup scripts.

## Services and Ports

- `client_index` -> `8002`
- `payments` -> `8003`
- `data_handling` -> `8004`
- `auditor` -> `8005`
- `orchestrator` -> `8006`
- `watchdog` -> `8007`
- `support_hub` -> `8008`
- `workforce_ops` -> `8009`

## One-time Setup

```bash
cd microservices
./install_deps.sh
```

## Start / Stop

```bash
cd microservices
./start_all.sh
./health_check.sh
```

```bash
cd microservices
./stop_all.sh
```

## Systemd (Production)

Install and enable all microservices as boot-persistent systemd units:

```bash
cd microservices
chmod +x systemd/install_systemd_services.sh systemd/uninstall_systemd_services.sh
./systemd/install_systemd_services.sh
```

Remove systemd units:

```bash
cd microservices
./systemd/uninstall_systemd_services.sh
```

## Gate and Rollback

Run go-live gate checks:

```bash
cd microservices
chmod +x gate_check.sh
./gate_check.sh
```

Run rollback command pack:

```bash
cd microservices
chmod +x rollback.sh
./rollback.sh
```

## Nginx API Routing

The repository Nginx config routes `/api/*` to orchestrator on port `8006`:

- File: `nginx-d31337m3.conf`
- Upstream: `http://127.0.0.1:8006/api/`

Apply nginx config on host:

```bash
sudo ./setup-nginx.sh
```

## Runbook Alignment

This setup follows the startup order in:

- `docs/agent_go_live_microservices.md`
- `docs/go_live_quick_runbook.md`

## Notes

- Logs are written to `microservices/logs/*.log`.
- PIDs are written to `microservices/pids/*.pid`.
- Secrets are read from environment variables; replace defaults before production.
