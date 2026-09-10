from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.cookies import ACCESS_COOKIE
from app.core.database import get_central_pool, reset_request_pool, set_request_pool
from app.core.security import decode_access_token
from app.core.tenant_db import get_tenant_pool

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    user_type: str
    tenant_id: UUID | None
    session_id: UUID
    tenant_access_session_id: UUID | None = None


async def get_current_principal(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Principal:
    raw_token = credentials.credentials if credentials and credentials.scheme.lower() == "bearer" else None
    if settings.auth_cookie_mode and not raw_token: raw_token = request.cookies.get(ACCESS_COOKIE)
    if not raw_token: raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = decode_access_token(raw_token)
        principal = Principal(UUID(payload["sub"]), payload["typ"], UUID(payload["tid"]) if payload.get("tid") else None, UUID(payload["sid"]), UUID(payload["tas"]) if payload.get("tas") else None)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
    if principal.user_type not in {"platform", "tenant"}: raise HTTPException(status_code=401, detail="Invalid user type")
    pool = get_central_pool()
    table = "platform_users" if principal.user_type == "platform" else "tenant_users"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"SELECT status FROM {table} WHERE id=%s", (str(principal.user_id),))
            row = await cur.fetchone()
            if not row or row[0] != "active": raise HTTPException(status_code=401, detail="User account is not active")
            await cur.execute("SELECT revoked_at,expires_at FROM auth_sessions WHERE id=%s", (str(principal.session_id),))
            session = await cur.fetchone()
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            if not session or session[0] is not None or session[1] <= now: raise HTTPException(status_code=401, detail="Session is no longer active")
            if principal.tenant_access_session_id:
                await cur.execute("SELECT tenant_id,expires_at,revoked_at FROM tenant_access_sessions WHERE id=%s AND platform_user_id=%s", (str(principal.tenant_access_session_id), str(principal.user_id)))
                access = await cur.fetchone()
                if not access or access[2] is not None or access[1] <= now or str(access[0]) != str(principal.tenant_id): raise HTTPException(status_code=401, detail="Tenant access session is no longer active")
    request.state.user_id = str(principal.user_id)
    request.state.user_type = principal.user_type
    request.state.tenant_id = str(principal.tenant_id) if principal.tenant_id else None
    return principal


async def require_platform(principal: Principal = Depends(get_current_principal)) -> Principal:
    if principal.user_type != "platform": raise HTTPException(status_code=403, detail="Platform access required")
    return principal


def require_platform_permission(permission_code: str):
    async def dependency(principal: Principal = Depends(require_platform)) -> Principal:
        pool = get_central_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 FROM platform_user_roles ur JOIN platform_roles r ON r.id=ur.platform_role_id LEFT JOIN platform_role_permissions rp ON rp.platform_role_id=r.id LEFT JOIN platform_permissions p ON p.id=rp.platform_permission_id WHERE ur.platform_user_id=%s AND (r.is_super_admin=1 OR p.code=%s) LIMIT 1", (str(principal.user_id), permission_code))
                if not await cur.fetchone(): raise HTTPException(status_code=403, detail="Insufficient platform permission")
        return principal
    return dependency


async def get_tenant_id_from_host(request: Request) -> UUID:
    hostname = (request.url.hostname or "").lower().rstrip(".")
    if hostname in {"localhost", "127.0.0.1", settings.platform_admin_host, "admin.localhost"}: raise HTTPException(status_code=400, detail="Tenant hostname is required")
    pool = get_central_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT t.id,t.status FROM tenant_domains d JOIN tenants t ON t.id=d.tenant_id WHERE d.hostname=%s LIMIT 1", (hostname,))
            row = await cur.fetchone()
    if not row or row[1] != "active": raise HTTPException(status_code=404, detail="School tenant not found")
    return UUID(str(row[0]))


async def _set_tenant_pool(tenant_id: UUID):
    return set_request_pool(await get_tenant_pool(tenant_id))


async def require_tenant(request: Request, principal: Principal = Depends(get_current_principal), tenant_id: UUID = Depends(get_tenant_id_from_host)):
    if principal.tenant_id != tenant_id: raise HTTPException(status_code=403, detail="Tenant context mismatch")
    if principal.user_type == "platform" and not principal.tenant_access_session_id: raise HTTPException(status_code=403, detail="Platform users must establish audited tenant access before tenant operations")
    token = await _set_tenant_pool(tenant_id)
    try:
        yield tenant_id
    finally:
        reset_request_pool(token)


def require_tenant_permission(permission_code: str):
    async def dependency(request: Request, principal: Principal = Depends(get_current_principal), tenant_id: UUID = Depends(get_tenant_id_from_host)):
        if principal.tenant_id != tenant_id: raise HTTPException(status_code=403, detail="Tenant context mismatch")
        if principal.user_type == "platform" and not principal.tenant_access_session_id: raise HTTPException(status_code=403, detail="Platform users must establish audited tenant access before tenant operations")
        central = get_central_pool()
        async with central.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 FROM tenant_memberships m JOIN tenant_membership_roles mr ON mr.membership_id=m.id JOIN tenant_roles r ON r.id=mr.role_id JOIN tenant_role_permissions rp ON rp.role_id=r.id JOIN tenant_permissions p ON p.id=rp.permission_id WHERE m.tenant_id=%s AND m.tenant_user_id=%s AND m.status='active' AND p.code=%s LIMIT 1", (str(tenant_id), str(principal.user_id), permission_code))
                if not await cur.fetchone(): raise HTTPException(status_code=403, detail="Insufficient tenant permission")
        token = await _set_tenant_pool(tenant_id)
        try:
            yield tenant_id
        finally:
            reset_request_pool(token)
    return dependency
