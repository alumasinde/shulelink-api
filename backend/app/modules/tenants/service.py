from uuid import UUID, uuid4
from fastapi import HTTPException
from app.core.database import get_pool
from app.modules.auth.schemas import CreateTenantRequest, TenantResponse

TENANT_PERMISSIONS = [
    ("school.structure.read", "View school structure"),
    ("school.structure.manage", "Manage school structure"),
    ("students.read", "View students and guardians"),
    ("students.manage", "Manage students and guardians"),
    ("students.enroll", "Enroll and place students"),
    ("students.documents", "Manage student documents"),
]
DOCUMENT_TYPES = [
    ("birth_certificate", "Birth Certificate", False),
    ("previous_school_report", "Previous School Report", False),
    ("transfer_certificate", "Transfer Certificate", False),
]

async def create_tenant(payload: CreateTenantRequest) -> TenantResponse:
    pool = get_pool()
    tenant_id = uuid4()
    host = f"{payload.slug}.localhost"
    tenant_status = "active" if payload.database_mode == "shared" else "provisioning"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1 FROM tenants WHERE slug=%s OR EXISTS (SELECT 1 FROM tenant_domains WHERE hostname=%s) LIMIT 1", (payload.slug, host))
            if await cur.fetchone(): raise HTTPException(status_code=409, detail="Tenant slug is already in use")
            await cur.execute("INSERT INTO tenants (id,name,slug,status,database_mode) VALUES (%s,%s,%s,%s,%s)",(str(tenant_id),payload.name.strip(),payload.slug,tenant_status,payload.database_mode))
            await cur.execute("INSERT INTO tenant_domains (id,tenant_id,hostname,is_primary,verified_at) VALUES (%s,%s,%s,1,NOW())",(str(uuid4()),str(tenant_id),host))
            role_ids={code:str(uuid4()) for code in ("school_admin","teacher","guardian")}
            await cur.execute("INSERT INTO tenant_roles (id,tenant_id,code,name,is_system) VALUES (%s,%s,'school_admin','School Administrator',1),(%s,%s,'teacher','Teacher',1),(%s,%s,'guardian','Guardian',1)",(role_ids['school_admin'],str(tenant_id),role_ids['teacher'],str(tenant_id),role_ids['guardian'],str(tenant_id)))
            permission_ids={}
            for code,name in TENANT_PERMISSIONS:
                pid=str(uuid4()); permission_ids[code]=pid
                await cur.execute("INSERT INTO tenant_permissions (id,tenant_id,code,name) VALUES (%s,%s,%s,%s)",(pid,str(tenant_id),code,name))
            for code in ("school.structure.read","school.structure.manage","students.read","students.manage","students.enroll","students.documents"):
                await cur.execute("INSERT INTO tenant_role_permissions (role_id,permission_id) VALUES (%s,%s)",(role_ids['school_admin'],permission_ids[code]))
            for code in ("school.structure.read","students.read"):
                await cur.execute("INSERT INTO tenant_role_permissions (role_id,permission_id) VALUES (%s,%s)",(role_ids['teacher'],permission_ids[code]))
            for code,name,required in DOCUMENT_TYPES:
                await cur.execute("INSERT INTO student_document_types (id,tenant_id,code,name,is_required) VALUES (%s,%s,%s,%s,%s)",(str(uuid4()),str(tenant_id),code,name,required))
            await cur.execute("INSERT INTO identity_audit_log (actor_type,action,target_type,target_id,tenant_id) VALUES ('platform','tenant.create','tenant',%s,%s)",(str(tenant_id),str(tenant_id)))
    return TenantResponse(id=tenant_id,name=payload.name.strip(),slug=payload.slug,status=tenant_status,database_mode=payload.database_mode,host=host)

async def list_tenants() -> list[TenantResponse]:
    pool=get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id,name,slug,status,database_mode FROM tenants ORDER BY name")
            rows=await cur.fetchall()
    return [TenantResponse(id=UUID(str(row[0])),name=row[1],slug=row[2],status=row[3],database_mode=row[4],host=f"{row[2]}.localhost") for row in rows]
