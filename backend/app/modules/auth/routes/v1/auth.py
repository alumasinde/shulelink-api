from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.config import settings
from app.core.dependencies import Principal, get_current_principal, require_platform_permission
from app.core.rate_limit import limiter
from app.core.database import get_pool
from app.modules.auth.schemas import LoginRequest, LogoutRequest, MeResponse, RefreshRequest, TokenResponse
from app.modules.auth.service import login_user, logout_session, refresh_session
from app.modules.tenants.schemas import TenantAccessRequest, TenantAccessResponse
from app.modules.tenants.access import establish_tenant_access, revoke_tenant_access

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/platform/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def platform_login(request: Request, payload: LoginRequest):
    if (request.url.hostname or "") not in {settings.platform_admin_host, "admin.localhost"}:
        raise HTTPException(status_code=404, detail="Platform authentication endpoint not available on this host")
    access, refresh, expires = await login_user(payload.email, payload.password, "platform")
    return TokenResponse(access_token=access, refresh_token=refresh, expires_at=expires)

@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def tenant_login(request: Request, payload: LoginRequest):
    from app.core.dependencies import get_tenant_id_from_host
    tenant_id = await get_tenant_id_from_host(request)
    access, refresh, expires = await login_user(payload.email, payload.password, "tenant", tenant_id)
    return TokenResponse(access_token=access, refresh_token=refresh, expires_at=expires)

@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh(request: Request, payload: RefreshRequest):
    access, refresh_token, expires = await refresh_session(payload.refresh_token)
    return TokenResponse(access_token=access, refresh_token=refresh_token, expires_at=expires)

@router.post("/logout")
async def logout(payload: LogoutRequest, principal: Principal = Depends(get_current_principal)):
    await logout_session(payload.refresh_token, principal.session_id)
    return {"success": True, "data": {"status": "logged_out"}}

@router.get("/me", response_model=MeResponse)
async def me(principal: Principal = Depends(get_current_principal)):
    table = "platform_users" if principal.user_type == "platform" else "tenant_users"
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"SELECT id,email,first_name,last_name FROM {table} WHERE id=%s", (str(principal.user_id),))
            row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return MeResponse(id=UUID(str(row[0])), email=row[1], first_name=row[2], last_name=row[3], user_type=principal.user_type, tenant_id=principal.tenant_id)

@router.post("/platform/tenant-access", response_model=TenantAccessResponse)
async def tenant_access(payload: TenantAccessRequest, principal: Principal = Depends(require_platform_permission("tenant.access"))):
    access, expires, access_id = await establish_tenant_access(principal.user_id, payload.tenant_id, payload.reason, principal.session_id)
    return TenantAccessResponse(access_token=access, expires_at=expires.isoformat(), tenant_access_session_id=access_id)

@router.delete("/platform/tenant-access/{access_id}")
async def revoke_access(access_id: UUID, principal: Principal = Depends(require_platform_permission("tenant.access"))):
    await revoke_tenant_access(principal.user_id, access_id)
    return {"success": True, "data": {"status": "revoked"}}
