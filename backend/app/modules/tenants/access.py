from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from fastapi import HTTPException
from app.core.database import get_pool
from app.core.security import create_access_token

async def establish_tenant_access(platform_user_id: UUID, tenant_id: UUID, reason: str, session_id: UUID):
    if len(reason.strip()) < 5:
        raise HTTPException(status_code=422, detail="A meaningful access reason is required")
    pool = get_pool()
    access_id = uuid4()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    expires = (datetime.now(timezone.utc) + timedelta(minutes=30)).replace(tzinfo=None)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT status FROM tenants WHERE id=%s", (str(tenant_id),))
            tenant = await cur.fetchone()
            if not tenant or tenant[0] != "active":
                raise HTTPException(status_code=404, detail="Tenant not found or inactive")
            await cur.execute("UPDATE tenant_access_sessions SET revoked_at=%s WHERE platform_user_id=%s AND tenant_id=%s AND revoked_at IS NULL", (now,str(platform_user_id),str(tenant_id)))
            await cur.execute("INSERT INTO tenant_access_sessions (id,platform_user_id,tenant_id,reason,expires_at) VALUES (%s,%s,%s,%s,%s)", (str(access_id),str(platform_user_id),str(tenant_id),reason.strip(),expires))
            await cur.execute("UPDATE auth_sessions SET tenant_access_session_id=%s,tenant_id=%s WHERE id=%s AND user_type='platform' AND user_id=%s", (str(access_id),str(tenant_id),str(session_id),str(platform_user_id)))
            await cur.execute("INSERT INTO identity_audit_log (actor_type,actor_id,tenant_id,action,target_type,target_id,metadata) VALUES ('platform',%s,%s,'tenant.access.start','tenant',%s,%s)", (str(platform_user_id),str(tenant_id),str(tenant_id),'{"duration_minutes":30}'))
    access, access_expires = create_access_token(user_id=str(platform_user_id),user_type="platform",tenant_id=str(tenant_id),session_id=str(session_id),access_session_id=str(access_id))
    return access, access_expires, access_id

async def revoke_tenant_access(platform_user_id: UUID, access_id: UUID):
    pool = get_pool()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT tenant_id FROM tenant_access_sessions WHERE id=%s AND platform_user_id=%s", (str(access_id),str(platform_user_id)))
            row = await cur.fetchone()
            await cur.execute("UPDATE tenant_access_sessions SET revoked_at=%s WHERE id=%s AND platform_user_id=%s AND revoked_at IS NULL", (now,str(access_id),str(platform_user_id)))
            if cur.rowcount:
                await cur.execute("UPDATE auth_sessions SET tenant_access_session_id=NULL,tenant_id=NULL WHERE user_type='platform' AND user_id=%s AND tenant_access_session_id=%s", (str(platform_user_id),str(access_id)))
                await cur.execute("INSERT INTO identity_audit_log (actor_type,actor_id,tenant_id,action,target_type,target_id) VALUES ('platform',%s,%s,'tenant.access.revoke','tenant_access_session',%s)", (str(platform_user_id),str(row[0]) if row else None,str(access_id)))
