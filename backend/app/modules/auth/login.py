from datetime import datetime, timezone
from uuid import UUID, uuid4
from fastapi import HTTPException, status
from app.core.database import get_pool
from app.core.security import create_access_token, create_refresh_token, verify_password


def unauthorized() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

async def login_user(email: str, password: str, user_type: str, tenant_id: UUID | None = None):
    pool = get_pool()
    table = "platform_users" if user_type == "platform" else "tenant_users"
    identifier = email.lower().strip()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            if user_type == "tenant":
                await cur.execute(f"SELECT id,email,first_name,last_name,password_hash,status FROM {table} WHERE email=%s OR login_identifier=%s LIMIT 1", (identifier, identifier))
            else:
                await cur.execute(f"SELECT id,email,first_name,last_name,password_hash,status FROM {table} WHERE email=%s LIMIT 1", (identifier,))
            user = await cur.fetchone()
            if not user or user[5] != "active" or not verify_password(password, user[4]):
                raise unauthorized()
            if user_type == "tenant":
                if tenant_id is None:
                    raise HTTPException(status_code=400, detail="Tenant context is required")
                await cur.execute("SELECT 1 FROM tenant_memberships WHERE tenant_id=%s AND tenant_user_id=%s AND status='active' LIMIT 1", (str(tenant_id), str(user[0])))
                if not await cur.fetchone():
                    raise unauthorized()
            session_id = uuid4()
            refresh_raw, refresh_hash, refresh_expires = create_refresh_token()
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            await cur.execute("INSERT INTO auth_sessions (id,user_type,user_id,tenant_id,refresh_token_hash,expires_at,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)", (str(session_id), user_type, str(user[0]), str(tenant_id) if tenant_id else None, refresh_hash, refresh_expires.replace(tzinfo=None), now))
            access, access_expires = create_access_token(user_id=str(user[0]), user_type=user_type, tenant_id=str(tenant_id) if tenant_id else None, session_id=str(session_id))
            await cur.execute(f"UPDATE {table} SET last_login_at=%s WHERE id=%s", (now, str(user[0])))
            await cur.execute("INSERT INTO identity_audit_log (actor_type,actor_id,tenant_id,action,target_type,target_id) VALUES (%s,%s,%s,'auth.login',%s,%s)", (user_type, str(user[0]), str(tenant_id) if tenant_id else None, user_type, str(user[0])))
            return access, refresh_raw, access_expires
