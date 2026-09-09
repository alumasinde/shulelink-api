# ShuleLink Enterprise Hardening

## Local development remains supported

The default development profile is intentionally unchanged:

- `APP_ENV=development`
- `AUTH_COOKIE_MODE=false`
- bearer access + refresh tokens remain available to the existing Vue local client
- `RATE_LIMIT_STORAGE_URI=memory://` is allowed locally
- local MariaDB/MySQL does not require TLS
- `AUTH_RESET_RETURN_TOKEN=true` can be used locally to test password recovery without an SMTP provider

After pulling the latest code, run the existing migration runner and restart FastAPI. Existing local tenant data is not converted to dedicated databases automatically.

## Production browser sessions

Set:

```env
APP_ENV=production
AUTH_COOKIE_MODE=true
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=lax
```

Access and refresh tokens are then held in Secure, HttpOnly cookies. State-changing requests require the CSRF cookie/header pair. Mobile and non-browser clients can continue using bearer tokens when cookie mode is disabled for that client.

## MFA

TOTP MFA is available for platform and tenant accounts, with one-time recovery codes. Enrollment:

1. Sign in normally.
2. `POST /api/v1/auth/mfa/enroll`.
3. Add the returned `otpauth_uri` to an authenticator app.
4. `POST /api/v1/auth/mfa/enroll/verify` with the current six-digit code.
5. Store the returned recovery codes offline.

Once MFA is enabled, login becomes a password + MFA challenge flow. Disabling MFA requires the current password and current TOTP code.

Operational policy should require MFA enrollment for `platform_admin`, `school_admin`, `registrar`, and `bursar` accounts before production access is granted.

## Password recovery

Password reset tokens are random, hashed before storage, single-use and short-lived. Production requires SMTP configuration and never returns reset tokens in API responses. Development can enable `AUTH_RESET_RETURN_TOKEN=true` for local testing only.

## Per-account throttling

IP-based rate limiting remains in place, with a database-backed per-account failure counter. Five failed authentication attempts within the active failure window lock the account identifier for 15 minutes. Successful authentication clears the counter.

## Dedicated tenant databases

The central application user is deliberately not granted `CREATE DATABASE`/`CREATE USER`. Configure a separate provisioner identity:

```env
DB_PROVISIONER_HOST=127.0.0.1
DB_PROVISIONER_PORT=3306
DB_PROVISIONER_USER=shulelink_provisioner
DB_PROVISIONER_PASSWORD=...
DB_PROVISIONER_TENANT_HOST=127.0.0.1
CREDENTIAL_ENCRYPTION_KEY=...
```

For a tenant created with `database_mode=dedicated`, run:

```powershell
cd backend
python scripts/provision_dedicated_tenant.py <TENANT_UUID>
```

The utility creates the database and least-privilege tenant DB user, applies the complete migration set, copies the tenant slice, encrypts the dedicated DB password in the central catalog, and then the normal tenant DB resolver uses that encrypted credential.

The normal web application DB user does not receive provisioning privileges.

## Database TLS

Production requires `DB_SSL_CA` and uses TLS for both the central pool and dedicated tenant pools. Keep `DB_SSL_VERIFY=true`.

## Audit and SIEM

Security events and request logs are emitted as structured JSON with request ID, actor, tenant, endpoint, status and duration fields. Ship stdout/stderr to the production logging/SIEM platform and configure retention/alerting there. Do not log passwords, access tokens, refresh tokens, MFA secrets or reset tokens.

## Backups and restore

Backups remain infrastructure-owned. Production must provide encrypted off-site backups, point-in-time recovery where supported, access-controlled backup credentials and a scheduled restore drill. The application intentionally does not attempt to implement database backup inside request handlers.

## Deployment checklist

Before production:

- HTTPS is terminated before browser traffic reaches the app.
- Redis is configured for distributed rate limiting.
- SMTP is configured and tested.
- `AUTH_COOKIE_MODE=true` and `AUTH_COOKIE_SECURE=true` are set for browser deployments.
- `CREDENTIAL_ENCRYPTION_KEY` is stored in a secret manager and rotated under a documented procedure.
- DB TLS is enabled and certificate verification remains on.
- Application DB user is not root/admin.
- Provisioner credentials are separate from application DB credentials.
- Platform and privileged tenant users have MFA enrolled.
- Backups and restore procedures have been tested.
- Structured logs are forwarded to centralized monitoring/SIEM.
