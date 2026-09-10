from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4
import secrets
from fastapi import HTTPException
from app.core.database import get_central_pool
from app.core.security import hash_password, hash_token, validate_password
ROLE_PORTALS={"school_admin":"school-admin","registrar":"registrar","bursar":"finance","teacher":"teacher","guardian":"parent","student":"student"}
ROLE_PRIORITY=["school_admin","registrar","bursar","teacher","guardian","student"]
async def get_role_context(user_id:UUID,user_type:str,tenant_id:UUID|None)->dict:
    pool=get_central_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            if user_type=="platform":
                await cur.execute("SELECT r.code,r.is_super_admin FROM platform_user_roles ur JOIN platform_roles r ON r.id=ur.platform_role_id WHERE ur.platform_user_id=%s ORDER BY r.code",(str(user_id),)); role_rows=await cur.fetchall(); roles=[str(r[0]) for r in role_rows]
                if any(bool(r[1]) for r in role_rows):
                    await cur.execute("SELECT code FROM platform_permissions ORDER BY code"); permissions=[str(r[0]) for r in await cur.fetchall()]
                else:
                    await cur.execute("SELECT DISTINCT p.code FROM platform_user_roles ur JOIN platform_role_permissions rp ON rp.platform_role_id=ur.platform_role_id JOIN platform_permissions p ON p.id=rp.platform_permission_id WHERE ur.platform_user_id=%s ORDER BY p.code",(str(user_id),)); permissions=[str(r[0]) for r in await cur.fetchall()]
                return {"roles":roles,"permissions":permissions,"portal":"platform"}
            if not tenant_id:raise HTTPException(403,"Tenant context required")
            await cur.execute("SELECT DISTINCT r.code FROM tenant_memberships m JOIN tenant_membership_roles mr ON mr.membership_id=m.id JOIN tenant_roles r ON r.id=mr.role_id WHERE m.tenant_id=%s AND m.tenant_user_id=%s AND m.status='active' ORDER BY r.code",(str(tenant_id),str(user_id))); roles=[str(r[0]) for r in await cur.fetchall()]
            await cur.execute("SELECT DISTINCT p.code FROM tenant_memberships m JOIN tenant_membership_roles mr ON mr.membership_id=m.id JOIN tenant_roles r ON r.id=mr.role_id JOIN tenant_role_permissions rp ON rp.role_id=r.id JOIN tenant_permissions p ON p.id=rp.permission_id WHERE m.tenant_id=%s AND m.tenant_user_id=%s AND m.status='active' ORDER BY p.code",(str(tenant_id),str(user_id))); permissions=[str(r[0]) for r in await cur.fetchall()]
    role=next((r for r in ROLE_PRIORITY if r in roles),None); return {"roles":roles,"permissions":permissions,"portal":ROLE_PORTALS.get(role,"school")}
async def create_activation(tenant_id:UUID,user_id:UUID,purpose:str)->tuple[str,datetime]:
    raw=secrets.token_urlsafe(48); expires=datetime.now(timezone.utc).replace(tzinfo=None,microsecond=0)+timedelta(hours=24); pool=get_central_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur: await cur.execute("INSERT INTO account_activation_tokens (id,tenant_id,tenant_user_id,token_hash,purpose,expires_at) VALUES (%s,%s,%s,%s,%s,%s)",(str(uuid4()),str(tenant_id),str(user_id),hash_token(raw),purpose,expires))
    return raw,expires
async def activate_account(token:str,password:str)->dict:
    try:validate_password(password)
    except ValueError as exc:raise HTTPException(422,str(exc))
    now=datetime.now(timezone.utc).replace(tzinfo=None); pool=get_central_pool()
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                await cur.execute("SELECT id,tenant_id,tenant_user_id,expires_at,consumed_at FROM account_activation_tokens WHERE token_hash=%s LIMIT 1 FOR UPDATE",(hash_token(token),)); row=await cur.fetchone()
                if not row or row[4] is not None or row[3]<=now:raise HTTPException(400,"Activation link is invalid or expired")
                await cur.execute("SELECT email,status FROM tenant_users WHERE id=%s",(str(row[2]),)); user=await cur.fetchone()
                if not user or user[1]!="active":raise HTTPException(400,"Account is not available for activation")
                await cur.execute("UPDATE tenant_users SET password_hash=%s WHERE id=%s",(hash_password(password),str(row[2]))); await cur.execute("UPDATE account_activation_tokens SET consumed_at=%s WHERE id=%s AND consumed_at IS NULL",(now,str(row[0])))
                if cur.rowcount!=1:raise HTTPException(400,"Activation link is invalid or already used")
                await cur.execute("INSERT INTO identity_audit_log (actor_type,actor_id,tenant_id,action,target_type,target_id) VALUES ('tenant',%s,%s,'auth.account.activate','tenant_user',%s)",(str(row[2]),str(row[1]),str(row[2]))); await conn.commit(); return {"message":"Account activated successfully. You can now sign in.","email":user[0],"expires_at":row[3]}
        except Exception:await conn.rollback();raise
