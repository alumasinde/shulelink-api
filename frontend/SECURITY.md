# ShuleLink Frontend Security

## Authentication

- Production builds automatically use secure cookie authentication.
- Access and refresh tokens are not intentionally persisted in browser storage in production.
- Local bearer-token storage exists only for development compatibility.
- CSRF tokens are fetched only when required for state-changing cookie-authenticated requests.
- Refresh requests are serialized so concurrent 401 responses do not rotate the refresh session repeatedly.
- Failed refreshes clear the local session and return the user to the normal authentication flow.

## API handling

- All application API modules should use the centralized Axios client in `src/api/client.js`.
- Do not create ad-hoc Axios clients for authenticated requests.
- Do not put secrets in `VITE_*` variables; Vite exposes these values to browser code.
- User-facing API errors are normalized so transport failures and server failures do not expose stack traces.

## Authorization

Frontend route and navigation permissions are for user experience only. The FastAPI backend remains the source of truth for authentication, tenant isolation, roles, and permissions.

Never add a frontend-only permission check as a substitute for a backend authorization check.

## Browser security

The application includes basic security metadata in `index.html`. Production hosting should also send security headers at the web-server/CDN layer, especially:

- Content-Security-Policy
- Strict-Transport-Security
- X-Content-Type-Options
- Referrer-Policy
- Permissions-Policy
- appropriate Cache-Control directives for authenticated application pages

CSP is intentionally not hardcoded into the HTML meta tags because the final policy must match the production hosting and API origins.

## File uploads

The frontend must treat file validation as user-experience validation only. MIME type, extension, file signature, size, authorization, and storage safety must be enforced by the backend.

Never render untrusted HTML with `v-html` and never construct executable URLs from untrusted API data.

## CI

Every frontend CI run performs:

1. `npm ci` using the committed lockfile.
2. `npm audit --audit-level=high --omit=dev`.
3. `npm run build`.

Dependency updates should be reviewed and committed together with the updated lockfile.
