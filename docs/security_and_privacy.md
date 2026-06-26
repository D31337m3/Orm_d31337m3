# Security & Privacy

This document outlines implemented and recommended security measures and privacy protections for the Orm_d31337m3 application. It is intended for maintainers and auditors.

## Goals

- Protect customer data confidentiality, integrity, and availability.
- Minimize collection and retention of personally identifiable information (PII).
- Provide clear operational steps for secure deployment and incident response.

## Summary of Implemented Controls

- Reverse proxy using Nginx (`nginx-d31337m3.conf`) to terminate and centralize HTTP traffic and headers.
- Separation of frontend (port 3000) and backend (port 8001) services with explicit proxy rules.
- Deployment script (`setup-nginx.sh`) installs site and removes default site to avoid serving unwanted content.

Note: TLS is not configured in the repo by default—enable it in production (see recommendations below).

## Network & Transport Security

- Enforce HTTPS (TLS 1.2/1.3) in production. Use Let's Encrypt / Certbot or a managed certificate service.
  - Example quick commands (Ubuntu):

```bash
sudo apt update
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

- Recommended Nginx headers (add to Nginx site config):

````nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Referrer-Policy "no-referrer-when-downgrade" always;
add_header X-XSS-Protection "1; mode=block" always;
# Consider a strict Content-Security-Policy tailored to the app
````

- Configure TLS securely: prefer modern ciphers, enable OCSP stapling, disable weak protocols.

## Authentication & Authorization

- Use strong session or token-based authentication (JWTs with short expiry or server-side sessions).
- Enforce least-privilege access for all internal services and database credentials.
- Implement account brute-force protections and rate limiting on authentication endpoints.
- Store password hashes with a modern KDF (bcrypt, Argon2) and enforce strong password policies.

## Data Protection (At-rest & In-transit)

- TLS for all client-server and service-to-service traffic.
- Encrypt sensitive data at rest (database encryption or filesystem-level encryption where appropriate).
- Use parameterized queries / ORM protections to avoid SQL injection.

## Input Validation & Output Encoding

- Validate all inputs on the server side (types, lengths, allowed values).
- Sanitize and encode outputs for HTML contexts to prevent XSS.
- Restrict allowed file uploads (type/size) and scan for malicious content.

## CORS, CSRF, and API Hardening

- Configure CORS to only allow approved origins in production.
- Protect state-changing endpoints from CSRF (CSRF tokens, same-site cookies).
- Require authentication on sensitive API endpoints and implement proper authorization checks.

## Logging, Monitoring & Privacy-aware Logging

- Log useful operational events (auth attempts, errors, admin actions) while redacting PII.
- Centralize logs and enable alerting for anomalous activity.
- Define a log retention period and implement secure log archival.

## Backup & Recovery

- Encrypt backups and store them off-site with access controls.
- Test restores regularly and maintain a documented recovery plan.

## Secrets & CI/CD

- Never commit secrets to the repository. Use environment variables, secret managers, or CI secret stores.
- Limit access to CI secrets and rotate them periodically.

## Server Hardening & Runtime Environment

- Run services as unprivileged users and minimize exposed ports.
- Use a host firewall (`ufw`) to restrict access:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'  # allows 80 and 443
sudo ufw enable
```

- Consider `fail2ban` to block repeated suspicious connections.
- Keep OS and dependencies updated and apply security patches promptly.

## Third-party Dependencies

- Pin dependency versions and scan dependencies for vulnerabilities (e.g., `snyk`, `dependabot`, `pip-audit`).
- Monitor advisories and apply updates for vulnerable packages.

## Privacy Protections

- Data minimization: collect only the data necessary to provide the service.
- PII handling:
  - Store PII encrypted at rest.
  - Limit access to PII to authorized personnel and services only.
  - Maintain an access log for data access operations.
- Deletion & retention:
  - Implement processes for data deletion on user request.
  - Maintain retention schedules for different classes of data and purge accordingly.
- Consent & transparency:
  - Provide clear user-facing privacy policy and obtain consent when required.

## Incident Response

- Maintain an incident response plan with contacts, escalation paths, and steps to contain and remediate breaches.
- Have procedures for legal/regulatory notification if PII is compromised.

## Operational Checklist for Production Deployment

- [ ] Enable HTTPS and HSTS
- [ ] Add secure headers to Nginx
- [ ] Configure strict CORS policies
- [ ] Harden the host (UFW, fail2ban)
- [ ] Set up centralized logging and monitoring
- [ ] Configure daily backups with encryption
- [ ] Run dependency vulnerability scans in CI
- [ ] Configure secret management for CI/CD

## Contact & Responsible Parties

List maintainers or security contacts here (email/role) for incident reporting.

---

This document should be reviewed periodically and updated whenever architecture or data handling practices change.