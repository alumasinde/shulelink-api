from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status

from app.core.database import get_pool
from app.core.security import create_access_token, create_refresh_token, hash_token, verify_password
from app.modules.auth.hardening_service import (
    clear_login_throttle,
    create_mfa_challenge,
    ensure_not_throttled,
    issue_session,
    mfa_enabled,
    record_login_failure,
)


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


async def login_user(email: str, password: str, user_type: str, tenant_id: UUID | None = None):
    pool = get_pool()
    table = "platform_users" if user_type == "platform" else "tenant_users"
    normalized = email.lower().strip()
    await ensure_not_throttled(user_type, normalized)

    async with pool.acquire() as conn:
        try:
            await conn.begin()
            async with conn.cursor() as cur:
                await cur.execute(f"SELECT id,email,first_name,last_name,password_hash,status FROM {table} WHERE email=%s LIMIT 1", (normalized,))
                user = await cur.fetchone()
                if not user or user[5] != "active" or not verify_password(password, user[4]):
                    await conn.rollback()
                    await record_login_failure(user_type, normalized)
                    raise _unauthorized()
                if user_type == "tenant":
                    if tenant_id is None:
                        await conn.rollback()
                        raise HTTPException(status_code=400, detail="Tenant context is required")
                    await cur.execute("SELECT 1 FROM tenant_memberships WHERE tenant_id=%s AND tenant_user_id=%s AND status='active' LIMIT 1", (str(tenant_id),str(user[0])))
                    if not await cur.fetchone():
                        await conn.rollback()
                        await record_login_failure(user_type, normalized)
                        raise _unauthorized()

                await cur.execute("SELECT 1 FROM mfa_factors WHERE user_type=%s AND user_id=%s AND factor_type='totp' AND enabled=1 LIMIT 1", (user_type,str(user[0])))
                has_mfa = bool(await cur.fetchone())
                if has_mfa:
                    challenge_id = await create_mfa_challenge(user_type, UUID(str(user[0])), tenant_id)
                    await conn.rollback()
                    await clear_login_throttle(user_type, normalized)
                    return {"mfa_required": True, "mfa_challenge_id": challenge_id, "access_token": None, "refresh_token": None, "expires_at": None}

                now = datetime.now(timezone.utc).replace(tzinfo=None)
                access, refresh_raw, access_expires, _ = await issue_session(conn, user_type, UUID(str(user[0])), tenant_id)
                await cur.execute(f"UPDATE {table} SET last_login_at=%s WHERE id=%s", (now,str(user[0])))
                await cur.execute("INSERT INTO identity_audit_log (actor_type,actor_id,tenant_id,action,target_type,target_id) VALUES (%s,%s,%s,'auth.login',%s,%s)", (user_type,str(user[0]),str(tenant_id) if tenant_id else None,user_type,str(user[0])))
                await conn.commit()
                await clear_login_throttle(user_type, normalized)
                return {"access_token": access, "refresh_token": refresh_raw, "expires_at": access_expires, "mfa_required": False, "mfa_challenge_id": None}
        except Exception:
            try:
                await conn.rollback()
            except Exception:
                pass
            raise


async def refresh_session(refresh_token: str):
    pool = get_pool()
    token_hash = hash_token(refresh_token)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id,user_type,user_id,tenant_id,tenant_access_session_id,expires_at,revoked_at FROM auth_sessions WHERE refresh_token_hash=%s LIMIT 1", (token_hash,))
            session = await cur.fetchone()
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            if not session or session[6] is not None or session[5] <= now:
                raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
            table = "platform_users" if session[1] == "platform" else "tenant_users"
            await cur.execute(f"SELECT status FROM {table} WHERE id=%s", (str(session[2]),))
            user = await cur.fetchone()
            if not user or user[0] != "active":
                raise HTTPException(status_code=401, detail="User account is not active")
            if session[4]:
                await cur.execute("SELECT expires_at,revoked_at FROM tenant_access_sessions WHERE id=%s", (str(session[4]),))
                access_session = await cur.fetchone()
                if not access_session or access_session[1] is not None or access_session[0] <= now:
                    raise HTTPException(status_code=401, detail="Tenant access session is no longer active")
            new_raw, new_hash, new_expires = create_refresh_token()
            await cur.execute("UPDATE auth_sessions SET refresh_token_hash=%s,expires_at=%s,last_used_at=%s WHERE id=%s", (new_hash,new_expires.replace(tzinfo=None),now,str(session[0])))
            access, access_expires = create_access_token(user_id=str(session[2]),user_type=session[1],tenant_id=str(session[3]) if session[3] else None,session_id=str(session[0]),access_session_id=str(session[4]) if session[4] else None)
            return access,new_raw,access_expires


async def logout_session(refresh_token: str | None, session_id: UUID | None):
    pool = get_pool()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            if refresh_token:
                await cur.execute("UPDATE auth_sessions SET revoked_at=%s WHERE refresh_token_hash=%s AND revoked_at IS NULL", (now,hash_token(refresh_token)))
            elif session_id:
                await cur.execute("UPDATE auth_sessions SET revoked_at=%s WHERE id=%s AND revoked_at IS NULL", (now,str(session_id)))
