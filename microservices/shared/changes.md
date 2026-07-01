# changes.md — shared

## 1.0.3 (2026-07-01)

### Changed
- Release alignment bump for coordinated production rollout and shared package parity.

## 1.0.2 (2026-07-01)

### Added
- **Durable legal document model**: Added `Document` ORM model with signing metadata, dispatch fields, and witness fields.
- **Witness metadata in API schema**: Extended `DocumentInDB` with witness fields (`witness_signed_*`, role, auto-fill flag).
- **Repositories**: Added `SignatureRepository` (latest/upsert) and `DocumentRepository` (create/list/get/delete/sign).

### Changed
- **Signature serialization**: `Signature.to_dict()` now includes `data_url` for owner-facing retrieval/update flows.

## 1.0.1 (2026-07-01)

### Changed
- **Retry-backoff for Infisical initialization**: `init_infisical()` and `load_service_secrets()`
  now wrap their Infisical API calls in `_with_retry_backoff()` with exponential backoff
  (base 1s, multiplier 2x, max 30s, jitter 10%) and up to 5 retries.
- **Infisical health tracking**: Added module-level globals (`_infisical_connected`,
  `_infisical_last_success`, `_infisical_last_failure`, `_infisical_error`,
  `_infisical_latency_ms`, `_infisical_retry_count`) and `get_infisical_status()`
  function for integration into the system health pipeline.
