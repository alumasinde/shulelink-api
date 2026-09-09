# ShuleLink Environment & Configuration

ShuleLink uses one application configuration contract across development, test, staging, and production. Environment variables are the deployment interface; `.env` files are only a local convenience.

## Environment contract

`APP_ENV` must be one of:

- `development` — local development; HTTP and in-memory rate limiting are allowed when explicitly configured.
- `test` — CI/test execution; use isolated test services and credentials.
- `staging` — production-like security controls with isolated infrastructure/data.
- `production` — production security and infrastructure controls; dedicated tenant provisioning credentials are required.

Unknown values fail startup. Missing required settings fail startup. Unknown `.env` keys fail startup as well; this prevents a misspelled variable from silently falling back to another value.

## Backend

Copy `backend/.env.example` to `backend/.env` for local development and fill in the values.

Reference templates:

- `backend/.env.example` — development
- `backend/.env.staging.example` — staging
- `backend/.env.production.example` — production

Do not rename a production template to a real production environment file and commit it. Inject production values through the hosting platform, container environment, or a secret manager.

### Configuration rules

1. There are no development defaults for deployment-sensitive backend settings such as database credentials, JWT secrets, CORS, trusted hosts, rate-limit storage, cookie mode, or reset URLs.
2. Production/staging reject debug mode, weak JWT secrets, root/admin DB users, memory rate limiting, insecure cookie mode, missing DB TLS CA, missing credential encryption keys, missing SMTP configuration, and production reset-token responses.
3. Production additionally requires dedicated-tenant DB provisioner credentials.
4. `TRUSTED_HOSTS` is authoritative. The application does not append localhost, testserver, the platform host, or the root domain automatically.
5. `CORS_ORIGINS` and optional `CORS_ORIGIN_REGEX` are authoritative. The application does not inject localhost or ShuleLink origins into CORS.
6. Tenant-specific database credentials are not stored in the process `.env`; they belong to the encrypted tenant database target configuration.

## Frontend

Vite variables are public build-time configuration. Never put passwords, JWT secrets, API keys, DB credentials, or encryption keys in `VITE_*` variables.

`frontend/.env.example` is the local template. `frontend/.env.production.example` is the production build template.

The browser derives the API URL from the current hostname so tenant resolution stays aligned with the hostname:

- local: `http://<host>:VITE_API_PORT/api/v1`
- production: `https://<current-shulelink-host>/api/v1`

An unsupported hostname causes the frontend to fail closed instead of selecting an arbitrary API endpoint.

Production builds always use cookie authentication. Local development must explicitly set `VITE_AUTH_COOKIE_MODE=true` or `false`.

## Local setup

```text
backend/.env.example  -> backend/.env
frontend/.env.example -> frontend/.env.local
```

The root `.gitignore` ignores real `.env` files while allowing only `*.example` templates to be committed.

## CI

CI must provide its own explicit `APP_ENV=test` configuration rather than relying on developer `.env` files. Production secrets must never be copied into CI configuration for ordinary tests.

## Deployment principle

Configuration is fail-fast, not fail-open:

```text
missing variable
      |
      v
startup validation
      |
      +---- invalid/missing ----> startup fails
      |
      +---- valid -------------> application starts
```

This is intentional. A production process must not start with a localhost database, development JWT secret, in-memory rate limiter, permissive host list, or another development fallback because an environment variable was forgotten.
