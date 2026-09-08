from uuid import UUID, uuid4
from fastapi import HTTPException
from app.core.database import get_pool
from app.modules.auth.schemas import CreateTenantRequest, TenantResponse

async def create_tenant(payload: CreateTenantRequest) -> TenantResponse:
    pool = get_pool()
    tenant_id = uuid4()
    host = f"{payload.slug}.localhost"
    tenant_status = "active" if payload.database_mode == "shared" else "provisioning"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1 FROM tenants WHERE slug=%s OR EXISTS (SELECT 1 FROM tenant_domains WHERE hostname=%s) LIMIT 1", (payload.slug, host))
            if await cur.fetchone():
                raise HTTPException(status_code=409, detail="Tenant slug is already in use")
            await cur.execute("INSERT INTO tenants (id,name,slug,status,database_mode) VALUES (%s,%s,%s,%s,%s)", (str(tenant_id),payload.name.strip(),payload.slug,tenant_status,payload.database_mode))
            await cur.execute("INSERT INTO tenant_domains (id,tenant_id,hostname,is_primary,verified_at) VALUES (%s,%s,%s,1,NOW())", (str(uuid4()),str(tenant_id),host))
            await cur.execute("INSERT INTO tenant_roles (id,tenant_id,code,name,is_system) VALUES (%s,%s,'school_admin','School Administrator',1),(%s,%s,'teacher','Teacher',1),(%s,%s,'guardian','Guardian',1)", (str(uuid4()),str(tenant_id),str(uuid4()),str(tenant_id),str(uuid4()),str(tenant_id)))
            await cur.execute("INSERT INTO identity_audit_log (actor_type,action,target_type,target_id,tenant_id) VALUES ('platform','tenant.create','tenant',%s,%s)", (str(tenant_id),str(tenant_id)))
    return TenantResponse(id=tenant_id,name=payload.name.strip(),slug=payload.slug,status=tenant_status,database_mode=payload.database_mode,host=host)

async def list_tenants() -> list[TenantResponse]:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id,name,slug,status,database_mode FROM tenants ORDER BY name")
            rows = await cur.fetchall()
    return [TenantResponse(id=UUID(str(row[0])),name=row[1],slug=row[2],status=row[3],database_mode=row[4],host=f"{row[2]}.localhost") for row in rows]
