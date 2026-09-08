from datetime import datetime, timezone
from uuid import UUID, uuid4
from fastapi import HTTPException, status
from app.core.database import get_pool
from app.core.security import create_access_token, create_refresh_token, hash_token, verify_password

def _unauthorized() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

async def login_user(email: str, password: str, user_type: str, tenant_id: UUID | None = None):
    pool = get_pool()
    table = "platform_users" if user_type == "platform" else "tenant_users"
    normalized = email.lower().strip()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"SELECT id,email,first_name,last_name,password_hash,status FROM {table} WHERE email=%s LIMIT 1", (normalized,))
            user = await cur.fetchone()
            if not user or user[5] != "active" or not verify_password(password, user[4]):
                raise _unauthorized()
            if user_type == "tenant":
                if tenant_id is None:
                    raise HTTPException(status_code=400, detail="Tenant context is required")
                await cur.execute("SELECT 1 FROM tenant_memberships WHERE tenant_id=%s AND tenant_user_id=%s AND status='active' LIMIT 1", (str(tenant_id),str(user[0])))
                if not await cur.fetchone():
                    raise _unauthorized()
            session_id = uuid4()
            refresh_raw, refresh_hash, refresh_expires = create_refresh_token()
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            await cur.execute("INSERT INTO auth_sessions (id,user_type,user_id,tenant_id,refresh_token_hash,expires_at,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)", (str(session_id),user_type,str(user[0]),str(tenant_id) if tenant_id else None,refresh_hash,refresh_expires.replace(tzinfo=None),now))
            access, access_expires = create_access_token(user_id=str(user[0]),user_type=user_type,tenant_id=str(tenant_id) if tenant_id else None,session_id=str(session_id))
            await cur.execute(f"UPDATE {table} SET last_login_at=%s WHERE id=%s", (now,str(user[0])))
            await cur.execute("INSERT INTO identity_audit_log (actor_type,actor_id,tenant_id,action,target_type,target_id) VALUES (%s,%s,%s,'auth.login',%s,%s)", (user_type,str(user[0]),str(tenant_id) if tenant_id else None,user_type,user[0]))
            return access, refresh_raw, access_expires

async def refresh_session(refresh_token: str):
    pool = get_pool()
    token_hash = hash_token(refresh_token)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id,user_type,user_id,tenant_id,expires_at,revoked_at FROM auth_sessions WHERE refresh_token_hash=%s LIMIT 1", (token_hash,))
            session = await cur.fetchone()
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            if not session or session[5] is not None or session[4] <= now:
                raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
            table = "platform_users" if session[1] == "platform" else "tenant_users"
            await cur.execute(f"SELECT status FROM {table} WHERE id=%s", (str(session[2]),))
            user = await cur.fetchone()
            if not user or user[0] != "active":
                raise HTTPException(status_code=401, detail="User account is not active")
            new_raw, new_hash, new_expires = create_refresh_token()
            await cur.execute("UPDATE auth_sessions SET refresh_token_hash=%s,expires_at=%s,last_used_at=%s WHERE id=%s", (new_hash,new_expires.replace(tzinfo=None),now,str(session[0])))
            access, access_expires = create_access_token(user_id=str(session[2]),user_type=session[1],tenant_id=str(session[3]) if session[3] else None,session_id=str(session[0]))
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
