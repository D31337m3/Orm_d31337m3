# changes.md — payments

## 1.0.4 (2026-07-01)

### Fixed
- **JWT claim compatibility**: Payment/subscription handlers now support user tokens carrying either `id`
  or `sub`, preventing 500 errors in subscribe/payment flows when only `sub` is present.

### Changed
- Release alignment bump for coordinated production rollout and service version parity.

## 1.0.3 (2026-07-01)

### Changed
- **Health endpoint version reporting**: `/health` now returns `version` (from `app.version`)
  and `started_at` (module-load timestamp) for display in the admin panel version table.

## 1.0.2 (2026-07-01)

### Changed
- Version bumped from 1.0.0 to 1.0.2 (parity update across all microservices).
