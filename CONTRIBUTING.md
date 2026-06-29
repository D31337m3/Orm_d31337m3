# Contributing

Thanks for contributing.

## Development Workflow

### Frontend

```bash
cd frontend
npm install
npm run build
```

### Microservices

```bash
cd microservices
./install_deps.sh
./start_all.sh
./health_check.sh
./stop_all.sh
```

## Testing Expectations

- Verify frontend builds successfully.
- Verify microservices health checks pass.
- Include reproduction and verification steps in your PR description.
- For production-impacting changes, include gate/rollback considerations.

## Pull Requests

- Keep changes focused and documented.
- Update related docs when behavior changes.
- Do not include secrets or sensitive environment files.

## Security Issues

Do not file sensitive security issues publicly. Contact maintainers directly through the configured private channel.
