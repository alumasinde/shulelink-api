from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from app.core.config import settings
from app.core.cookies import CSRF_COOKIE, clear_auth_cookies, set_auth_cookies
from app.core.database import get_pool
from app.core.dependencies import Principal, get_current_principal, get_tenant_id_from_host, require_platform_permission
from app.core.logging import logger
from app.core.rate_limit import limiter
from app.modules.auth.access import activate_account, get_role_context
from app.modules.auth.hardening_service import begin_mfa_enrollment, confirm_password_reset, disable_mfa, mfa_status, request_password_reset, verify_mfa_challenge, verify_mfa_enrollment
from app.modules.auth.mfa_reauth import verify_mfa_disable_credentials
from app.modules.auth.schemas import ActivateAccountRequest, ActivationResponse, LoginRequest, LogoutRequest, MeResponse, MFAChallengeRequest, MFAEnrollResponse, MFARecoveryResponse, MFAStatusResponse, MFADisableRequest, MFAVerifyEnrollmentRequest, PasswordResetConfirmRequest, PasswordResetRequest, RefreshRequest, TokenResponse
from app.modules.auth.service import login_user, logout_session, refresh_session
from app.modules.tenants.access import establish_tenant_access, revoke_tenant_access
from app.modules.tenants.schemas import TenantAccessRequest, TenantAccessResponse

router=APIRouter(prefix="/auth",tags=["Authentication"])

async def _login(request,response,payload,user_type,tenant_id=None):
    try:
        result=await login_user(payload.email,payload.password,user_type,tenant_id)
        logger.info("authentication succeeded",extra={"event":"authn_login_success","method":request.method,"path":request.url.path,"status_code":200,"user_type":user_type,"tenant_id":str(tenant_id) if tenant_id else None})
        if settings.auth_cookie_mode and not result["mfa_required"]:
            set_auth_cookies(response,result["access_token"],result["refresh_token"]); result={**result,"access_token":None,"refresh_token":None}
        return TokenResponse(**result)
    except Exception:
        logger.warning("authentication failed",extra={"event":"authn_login_failure","method":request.method,"path":request.url.path,"status_code":401,"user_type":user_type,"tenant_id":str(tenant_id) if tenant_id else None}); raise

@router.get("/csrf")
async def csrf(response:Response):
    if not settings.auth_cookie_mode:return {"enabled":False}
    import secrets
    token=secrets.token_urlsafe(settings.csrf_token_bytes); response.set_cookie(CSRF_COOKIE,token,max_age=settings.refresh_token_days*86400,secure=settings.auth_cookie_secure,httponly=False,samesite=settings.auth_cookie_samesite.lower(),path="/"); return {"enabled":True}

@router.post("/platform/login",response_model=TokenResponse)
@limiter.limit("5/minute")
async def platform_login(request:Request,response:Response,payload:LoginRequest):
    if (request.url.hostname or "") not in {settings.platform_admin_host,"admin.localhost"}:raise HTTPException(404,"Platform authentication endpoint not available on this host")
    return await _login(request,response,payload,"platform")

@router.post("/login",response_model=TokenResponse)
@limiter.limit("5/minute")
async def tenant_login(request:Request,response:Response,payload:LoginRequest): return await _login(request,response,payload,"tenant",await get_tenant_id_from_host(request))

@router.post("/mfa/verify",response_model=TokenResponse)
@limiter.limit("10/minute")
async def mfa_verify(request:Request,response:Response,payload:MFAChallengeRequest):
    access,refresh,expires,_=await verify_mfa_challenge(payload.challenge_id,payload.code)
    if settings.auth_cookie_mode:set_auth_cookies(response,access,refresh); access=refresh=None
    return TokenResponse(access_token=access,refresh_token=refresh,expires_at=expires)

@router.get("/mfa/status",response_model=MFAStatusResponse)
async def mfa_status_route(principal:Principal=Depends(get_current_principal)):return await mfa_status(principal.user_type,principal.user_id)

@router.post("/mfa/enroll",response_model=MFAEnrollResponse)
async def mfa_enroll(principal:Principal=Depends(get_current_principal)):
    table="platform_users" if principal.user_type=="platform" else "tenant_users"; pool=get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur: await cur.execute(f"SELECT email FROM {table} WHERE id=%s",(str(principal.user_id),)); row=await cur.fetchone()
    if not row:raise HTTPException(404,"User not found")
    fid,secret,uri=await begin_mfa_enrollment(principal.user_type,principal.user_id,row[0]); return MFAEnrollResponse(factor_id=fid,secret=secret,otpauth_uri=uri)

@router.post("/mfa/enroll/verify",response_model=MFARecoveryResponse)
@limiter.limit("10/minute")
async def mfa_enroll_verify(request:Request,payload:MFAVerifyEnrollmentRequest,principal:Principal=Depends(get_current_principal)):return MFARecoveryResponse(recovery_codes=await verify_mfa_enrollment(principal.user_type,principal.user_id,payload.code))

@router.delete("/mfa")
async def mfa_disable(payload:MFADisableRequest,principal:Principal=Depends(get_current_principal)):
    await verify_mfa_disable_credentials(principal.user_type,principal.user_id,payload.password,payload.code); await disable_mfa(principal.user_type,principal.user_id); return {"success":True,"data":{"status":"disabled"}}

@router.post("/password-reset/request")
@limiter.limit("5/minute")
async def password_reset_request(request:Request,payload:PasswordResetRequest):
    tenant_id=None if payload.user_type=="platform" else await get_tenant_id_from_host(request); token=await request_password_reset(payload.user_type,payload.email,tenant_id); data={"message":"If the account exists, password reset instructions have been sent."}
    if settings.auth_reset_return_token and token:data["development_token"]=token
    return {"success":True,"data":data}

@router.post("/password-reset/confirm")
@limiter.limit("10/minute")
async def password_reset_confirm(request:Request,payload:PasswordResetConfirmRequest):await confirm_password_reset(payload.token,payload.password); return {"success":True,"data":{"message":"Password reset successfully. Please sign in again."}}

@router.post("/activate",response_model=ActivationResponse)
@limiter.limit("5/minute")
async def activate(request:Request,payload:ActivateAccountRequest):return ActivationResponse(**await activate_account(payload.token,payload.password))

@router.post("/refresh",response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh(request:Request,response:Response,payload:RefreshRequest):
    raw=payload.refresh_token or request.cookies.get("__Host-shulelink_refresh")
    if not raw:raise HTTPException(401,"Refresh token is required")
    access,refresh_token,expires=await refresh_session(raw)
    if settings.auth_cookie_mode:set_auth_cookies(response,access,refresh_token); access=refresh_token=None
    return TokenResponse(access_token=access,refresh_token=refresh_token,expires_at=expires)

@router.post("/logout")
async def logout(request:Request,response:Response,payload:LogoutRequest,principal:Principal=Depends(get_current_principal)):
    await logout_session(payload.refresh_token or request.cookies.get("__Host-shulelink_refresh"),principal.session_id)
    if settings.auth_cookie_mode:clear_auth_cookies(response)
    return {"success":True,"data":{"status":"logged_out"}}

@router.get("/me",response_model=MeResponse)
async def me(principal:Principal=Depends(get_current_principal)):
    table="platform_users" if principal.user_type=="platform" else "tenant_users"; pool=get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur: await cur.execute(f"SELECT id,email,first_name,last_name FROM {table} WHERE id=%s",(str(principal.user_id),)); row=await cur.fetchone()
    if not row:raise HTTPException(404,"User not found")
    return MeResponse(id=UUID(str(row[0])),email=row[1],first_name=row[2],last_name=row[3],user_type=principal.user_type,tenant_id=principal.tenant_id,**(await get_role_context(principal.user_id,principal.user_type,principal.tenant_id)))

@router.get("/context")
async def context(principal:Principal=Depends(get_current_principal)):return await get_role_context(principal.user_id,principal.user_type,principal.tenant_id)

@router.post("/platform/tenant-access",response_model=TenantAccessResponse)
async def tenant_access(payload:TenantAccessRequest,principal:Principal=Depends(require_platform_permission("tenant.access"))):
    access,expires,access_id=await establish_tenant_access(principal.user_id,payload.tenant_id,payload.reason,principal.session_id); return TenantAccessResponse(access_token=access,expires_at=expires.isoformat(),tenant_access_session_id=access_id)

@router.delete("/platform/tenant-access/{access_id}")
async def revoke_access(access_id:UUID,principal:Principal=Depends(require_platform_permission("tenant.access"))):await revoke_tenant_access(principal.user_id,access_id); return {"success":True,"data":{"status":"revoked"}}
