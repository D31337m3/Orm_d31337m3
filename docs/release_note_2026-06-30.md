# Release Note - 2026-06-30

## Summary

This update finalizes frontend broker-submission workflows, landing telemetry layout adjustments, branding alignment, and repository cleanup with a security-first posture.

## Security-First Highlights

- Public landing telemetry now explicitly limits output to public-safe service health data.
- Sensitive diagnostics remain redacted from public views to reduce information disclosure risk.
- Broker submissions from authenticated users are routed through API support ticket intake.
- Public broker submissions are captured through controlled support intake mail flow.
- Existing JWT + secrets management architecture remains in place:
  - JWT verification in shared middleware/utilities
  - Infisical-first secret retrieval with environment fallback

## Frontend and UX Changes

- Added `Submit Broker` entry points on:
  - Landing page
  - User dashboard
- Added broker submission dialog supporting:
  - Required broker metadata fields (business name, address, privacy email, phone, country, lookup URL, notes)
  - CSV upload and parser
  - CSV header alias mapping and row-level validation
  - Inline preview of parsed broker rows
  - Downloadable CSV template
- Moved `service.health (public)` into the right-side live feed frame and aligned style/formatting.
- Updated shared `BrandMark` rendering to use official runtime logo assets.

## Branding and Asset Pipeline

- Runtime brand assets are now served from `frontend/public/`.
- Source branding payload is maintained in `brand_assets/`.
- Removed duplicate/temporary branding artifacts from public-facing repository surface.

## Repository Hygiene

- Removed obsolete or duplicate visual artifacts not required for runtime UI.
- Kept intentional deletions as part of repository cleanup.
- Documentation refreshed to remove references to retired verification script paths.

## Validation

- Frontend production build completed successfully after changes.
- No compile-time errors in updated broker submission component.

## Operational Note

For service readiness checks, use:

```bash
cd microservices
./health_check.sh
```

For security controls and privacy practices, see `docs/security_and_privacy.md`.
