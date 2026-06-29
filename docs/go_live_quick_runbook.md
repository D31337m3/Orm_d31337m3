# Go-Live Quick Runbook (Microservices)

Use this one-page runbook during the production cutover window.

## Scope

- `orchestrator`
- `client_index`
- `payments`
- `data_handling`
- `auditor`
- `watchdog`

## Hard Stop Rules

- Stop rollout on sustained 5xx spikes.
- Stop rollout on authentication failures.
- Stop rollout on payment conversion failures.
- Stop rollout if `auditor` ingest fails.

## T-60 Minutes (Prep)

1. Start change freeze.
2. Confirm on-call coverage and escalation contacts.
3. Confirm rollback artifact/version is ready.
4. Confirm latest backups completed and restore tested.

## T-30 Minutes (Validation)

1. Verify all services return healthy readiness checks.
2. Verify certificates, DNS, and ingress routing.
3. Confirm alerts and dashboards are live.
4. Capture baseline metrics snapshot.

## T-0 (Canary Start)

1. Route 5% traffic to new microservices stack.
2. Run smoke tests:
   - Login and token validation (`client_index`)
   - Trial to paid upgrade (`payments`)
   - Data query and indexing path (`data_handling`)
   - Audit event write/read (`auditor`)
3. Monitor latency, error rate, and business KPIs for 15 minutes.

## T+30 Minutes

1. If stable, increase canary to 25%.
2. Re-run smoke tests.
3. Verify no alert regressions.

## T+60 Minutes

1. If stable, increase to 50%.
2. Hold and monitor.
3. If stable, increase to 100%.

## Post-Cutover Validation (Immediately)

1. Confirm request success rate and latency SLO.
2. Confirm payment webhook and reconciliation path.
3. Confirm audit event throughput and storage integrity.
4. Confirm watchdog health view is green for all services.

## Rollback Procedure (If Triggered)

1. Route traffic back to previous stable stack.
2. Disable risky write paths if data integrity is uncertain.
3. Validate core user flows on rollback stack.
4. Open incident timeline and preserve logs/traces.

## Sign-Off Checklist

- [ ] All rollout gates passed.
- [ ] No P0/P1 incidents.
- [ ] Payment and auth flows validated.
- [ ] Audit pipeline validated.
- [ ] Rollback readiness remains available.
- [ ] GO decision recorded with approvers.
