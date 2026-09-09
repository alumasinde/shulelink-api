from datetime import datetime, timezone
from uuid import UUID, uuid4
import secrets

from fastapi import HTTPException

from app.core.database import get_central_pool
from app.core.security import hash_password
from app.modules.auth.access import create_activation


async def _create_account(tenant_id: UUID, first_name: str, last_name: str, role_code: str, purpose: str, email: str | None, login_identifier: str | None):
    pool = get_central_pool()
    user_id = uuid4()
    placeholder_password = hash_password(secrets.token_urlsafe(48))
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                await cur.execute("SELECT id FROM tenant_roles WHERE tenant_id=%s AND code=%s", (str(tenant_id), role_code))
                role = await cur.fetchone()
                if not role: raise HTTPException(422, f"Role {role_code} is not configured for this school")
                if email:
                    await cur.execute("SELECT 1 FROM tenant_users u JOIN tenant_memberships m ON m.tenant_user_id=u.id WHERE m.tenant_id=%s AND m.status='active' AND u.email=%s", (str(tenant_id), email.lower().strip()))
                    if await cur.fetchone(): raise HTTPException(409, "An account with that email already exists in this school")
                if login_identifier:
                    await cur.execute("SELECT 1 FROM tenant_users u JOIN tenant_memberships m ON m.tenant_user_id=u.id WHERE m.tenant_id=%s AND m.status='active' AND u.login_identifier=%s", (str(tenant_id), login_identifier.lower().strip()))
                    if await cur.fetchone(): raise HTTPException(409, "That login identifier is already in use in this school")
                await cur.execute("INSERT INTO tenant_users (id,email,login_identifier,first_name,last_name,password_hash,status) VALUES (%s,%s,%s,%s,%s,%s,'active')", (str(user_id), email.lower().strip() if email else None, login_identifier.lower().strip() if login_identifier else None, first_name.strip(), last_name.strip(), placeholder_password))
                membership_id = uuid4()
                await cur.execute("INSERT INTO tenant_memberships (id,tenant_id,tenant_user_id,status,joined_at) VALUES (%s,%s,%s,'active',NOW())", (str(membership_id), str(tenant_id), str(user_id)))
                await cur.execute("INSERT INTO tenant_membership_roles (membership_id,role_id) VALUES (%s,%s)", (str(membership_id), str(role[0])))
                await conn.commit()
        except Exception:
            await conn.rollback()
            raise
    token, expires = await create_activation(tenant_id, user_id, purpose)
    return {"user_id": str(user_id), "activation_token": token, "activation_expires_at": expires}
