# Frontend

React frontend for Orm_d31337m3.

## Current Highlights

- Unified brand rendering via `src/components/BrandMark.jsx` and `frontend/public` runtime assets.
- Broker submission dialog available on:
	- landing page (public intake)
	- user dashboard (authenticated intake)
- Broker submission supports:
	- manual form fields (business name, address, privacy email, phone, country, lookup URL, notes)
	- CSV upload and parsing with validation
	- downloadable CSV template
- Public service health is displayed under live feed on landing page, and intentionally redacts sensitive diagnostics.

## Security Notes

- Public pages only present sanitized service-health telemetry.
- Detailed internal diagnostics remain out of public frontend views.
- Authenticated submissions use API ticket intake; public submissions route to support intake mail.

## Scripts

```bash
npm install
npm start
npm run build
npm test
```

## API Integration

The frontend expects API routes under `/api` and is designed to work with the orchestrator-backed microservices deployment.

## Admin Console

The admin interface includes operations workflows for:

- user administration
- payment operations
- health and telemetry visibility
- service-state actions through orchestrator-compatible endpoints

For microservices operations and deployment controls, see `microservices/README.md`.
