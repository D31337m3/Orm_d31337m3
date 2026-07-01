# changes.md — workforce_ops

## 1.0.7 (2026-07-01)

### Changed
- Release alignment bump for coordinated production rollout and service version parity.

## 1.0.6 (2026-07-01)

### Added
- **Persistent in-memory store snapshots**: Added atomic JSON state save/load for shifts, timesheets, and payroll runs.

### Changed
- **Write durability**: Create/update/eviction paths now checkpoint state so workforce data survives restarts/reboots.

## 1.0.5 (2026-07-01)

### Changed
- **Health endpoint version reporting**: `/health` now returns `version` (from `app.version`)
  and `started_at` (module-load timestamp) for display in the admin panel version table.

## 1.0.4 (2026-07-01)

### Fixed
- **Startup crash after import reorder**: The 1.0.3 fix added `from shared.jwt_utils import *`
  and `from shared.security_middleware import *` which pulled in transitive dependencies that
  failed to resolve. Stripped down imports to only what main.py directly uses
  (`now_iso`, `init_infisical`, `get_cors_allowed_origins`).

## 1.0.3 (2026-07-01)

### Fixed
- **Import ordering crash**: `init_infisical()` was called before `sys.path.append` and the
  `from shared.secrets_manager import init_infisical` import, causing a `NameError` at module
  load time. Reordered to match the orchestrator's pattern: `sys.path.append` first, then
  imports, then `init_infisical()` call.

### Changed
- Added to `watchdog/service/routes.py` `DEFAULT_SERVICE_URLS` as `http://127.0.0.1:8009`
  so the watchdog monitors this service.
- Added to `orchestrator/service/main.py` `SERVICE_STARTUP_ORDER` as entry #6.
- Added to `microservices/health_check.sh` as `workforce_ops:8009`.
- Version bumped from 1.0.0 to 1.0.3.
