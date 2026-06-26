# Future Development

This document is a collection of ideas and plans for future development directions. We welcome contributions and feedback from the community. Please submit issues or pull requests for any suggestions or improvements.

## Architecture Improvements

(Immeninent Todo:) *Next release will be a refactor the backend to support a more modular architecture, potentially moving towards a microservices approach.*
- Microservices vs monolith: evaluate splitting backend into separate services for auth, billing, and core API as complexity grows.
- Move static assets to a CDN and serve a minimal Nginx layer for edge caching.
- Introduce a service mesh (e.g., Istio, Linkerd) when the number of services and inter-service policies grows.

## Developer Productivity

- Add a `Makefile` or `task` commands for common flows: `make dev`, `make test`, `make build`.
- Add GitHub Actions CI workflows for linting, testing, and dependency scanning.

## Observability & Reliability

- Integrate OpenTelemetry for distributed tracing and Prometheus/Grafana for metrics.
- Define SLOs and alerting rules; implement synthetic checks and uptime monitoring.

## Advanced Security & Privacy

- Harden defaults with automated policy checks (CIS benchmarks, infrastructure as code scanning).
- Implement token introspection and centralized auth for microservices.

## Data & ML Opportunities

- Define anonymized analytics pipelines for product improvement while preserving privacy.
- Consider ML-based monitoring for anomaly detection in traffic or user behavior (privacy-first approach).

## Internationalization & Accessibility

- Plan for localization and accessibility improvements to reach wider audiences.

## Monetization & Enterprise Features

- Add multi-tenant support, role-based access controls, and invoicing/billing integrations for enterprise needs.

## Open Questions

- When to introduce schema migrations vs manual SQL in production?
- Which managed cloud services (DB, cache, secrets) are chosen for long-term cost/maintenance tradeoffs?

## Next Steps

- Prioritize feature requests from users and stakeholders and map them to roadmap milestones.
- Keep this file as a live notes area for future proposals and RFCs.
