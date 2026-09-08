# Phase 2 — Identity + Multi-tenancy

Phase 2 adds the identity and tenant boundary used by all future ShuleLink modules.

## Identity model
- `platform_users`: ShuleLink staff/admin accounts; never carry `tenant_id`.
- `tenant_users`: reusable user identities for school users.
- `tenant_memberships`: connects a tenant user to one or more schools.
- Platform and tenant roles/permissions are separate.
- Refresh tokens are stored only as SHA-256 hashes.
- Access tokens are short-lived JWTs; refresh tokens rotate on use.
- Sessions and privileged tenant access are revocable.

## Tenant model
- `tenants` is the central tenant catalog.
- `tenant_domains` maps hostnames to tenants.
- Shared tenants use the central database.
- Dedicated tenants are represented in the catalog and are resolved by the tenant database manager; unprovisioned dedicated tenants fail closed.
- Tenant business tables must retain `tenant_id` even when a dedicated database is used.
- Tenant context is resolved from the request hostname, not an arbitrary client-supplied tenant id.

## Platform access to a tenant
A platform user cannot silently impersonate a school. They must create a short-lived, reason-coded `tenant_access_session`. The resulting token carries that access-session id and every start/revoke action is audited.

## Local bootstrap
After running migrations, create the first platform administrator:

```powershell
python scripts/create_platform_admin.py --email admin@example.com --first-name Admin --last-name User
```

For local tenant testing, tenants use `<slug>.localhost` (for example `demo.localhost`).

## Phase 2 endpoints
- `POST /api/v1/auth/platform/login`
- `POST /api/v1/auth/login` on a tenant hostname
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/platform/tenant-access`
- `DELETE /api/v1/auth/platform/tenant-access/{access_id}`
- `POST /api/v1/tenants`
- `GET /api/v1/tenants`
- `POST /api/v1/tenants/{tenant_id}/users`
- `GET /api/v1/tenant/context` on an authenticated tenant hostname
