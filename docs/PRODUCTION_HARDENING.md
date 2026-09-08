# ShuleLink Production Hardening

## Rate limiting

Development may use `RATE_LIMIT_STORAGE_URI=memory://`.
Production must use a shared store, for example:

```env
RATE_LIMIT_STORAGE_URI=redis://:PASSWORD@redis.internal:6379/0
RATE_LIMIT_DEFAULT=120/minute
```

Authentication is intentionally stricter:

- platform login: 5/minute
- tenant login: 5/minute
- account activation: 5/minute
- token refresh: 10/minute
- portal-account provisioning: 10/minute
- activation resend: 5/minute

A shared Redis backend is required when running multiple workers or multiple API instances so limits are consistent across instances.

## Structured logging

The API emits JSON logs containing the request ID, event, method, path, status, duration, client IP, authenticated user ID/type and tenant ID when available.

Do not log passwords, bearer tokens, refresh tokens, activation tokens or request bodies containing sensitive information.

Forward stdout/stderr to the production log collector/SIEM and retain security events according to the organization's retention policy.

## Database pooling

Each API process owns its own aiomysql pool. Configure `DB_POOL_MIN_SIZE` and `DB_POOL_MAX_SIZE` per process, not per cluster.

Example:

```env
DB_POOL_MIN_SIZE=5
DB_POOL_MAX_SIZE=20
DB_POOL_RECYCLE_SECONDS=1800
DB_CONNECT_TIMEOUT_SECONDS=10
DB_READ_TIMEOUT_SECONDS=30
DB_WRITE_TIMEOUT_SECONDS=30
```

If 4 worker processes use a max pool of 20, the database may receive up to approximately 80 application connections from that instance. Size MySQL/MariaDB `max_connections` accordingly and leave headroom for administration, migrations and other services.

## Production configuration

The application refuses production startup configuration that uses:

- debug mode
- the default JWT secret
- a JWT secret shorter than 32 characters
- root/admin as the application database user
- in-process (`memory://`) rate limiting

JWTs are validated with issuer and audience as well as signature, algorithm and required claims.

## Health checks

- `/api/v1/health` is a liveness check.
- `/api/v1/health/ready` checks database readiness and returns HTTP 503 when the database is unavailable.

## Tenant isolation

Tenant context is derived from the registered hostname and authenticated session. Client-supplied tenant IDs must not be trusted for selecting the tenant database or bypassing authorization.

## Deployment requirements still outside this application

Before production launch, deploy behind HTTPS/TLS termination, use a managed or hardened Redis service, use a least-privilege database account, enable encrypted database connections where supported, configure encrypted backups and restore testing, centralize logs, and establish monitoring/alerting.
