from uuid import UUID, uuid4
from fastapi import HTTPException
from app.core.database import get_pool
from app.core.security import hash_password, validate_password
from app.modules.tenants.schemas import CreateTenantUserRequest, TenantUserResponse

async def create_tenant_user(tenant_id: UUID, payload: CreateTenantUserRequest) -> TenantUserResponse:
    try:
        validate_password(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    pool = get_pool()
    user_id, membership_id = uuid4(), uuid4()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1 FROM tenants WHERE id=%s AND status='active'", (str(tenant_id),))
            if not await cur.fetchone():
                raise HTTPException(status_code=404, detail="Tenant not found or inactive")
            await cur.execute("SELECT 1 FROM tenant_users WHERE email=%s", (payload.email.lower().strip(),))
            if await cur.fetchone():
                raise HTTPException(status_code=409, detail="A user with that email already exists")
            await cur.execute("SELECT id FROM tenant_roles WHERE tenant_id=%s AND code=%s", (str(tenant_id),payload.role_code))
            role = await cur.fetchone()
            if not role:
                raise HTTPException(status_code=422, detail="Role does not exist for this tenant")
            await cur.execute("INSERT INTO tenant_users (id,email,first_name,last_name,password_hash,status) VALUES (%s,%s,%s,%s,%s,'active')", (str(user_id),payload.email.lower().strip(),payload.first_name.strip(),payload.last_name.strip(),hash_password(payload.password)))
            await cur.execute("INSERT INTO tenant_memberships (id,tenant_id,tenant_user_id,status,joined_at) VALUES (%s,%s,%s,'active',NOW())", (str(membership_id),str(tenant_id),str(user_id)))
            await cur.execute("INSERT INTO tenant_membership_roles (membership_id,role_id) VALUES (%s,%s)", (str(membership_id),str(role[0])))
            await cur.execute("INSERT INTO identity_audit_log (actor_type,tenant_id,action,target_type,target_id) VALUES ('system',%s,'tenant.user.create','tenant_user',%s)", (str(tenant_id),str(user_id)))
    return TenantUserResponse(id=user_id,tenant_id=tenant_id,email=payload.email.lower().strip(),first_name=payload.first_name.strip(),last_name=payload.last_name.strip(),role_code=payload.role_code,status="active")
