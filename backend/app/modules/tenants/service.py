from uuid import UUID, uuid4

from fastapi import HTTPException

from app.core.config import settings
from app.core.database import get_pool
from app.modules.auth.schemas import CreateTenantRequest, TenantResponse

TENANT_PERMISSIONS = [
    ("school.structure.read", "View school structure"),
    ("school.structure.manage", "Manage school structure"),
    ("students.read", "View students and guardians"),
    ("students.manage", "Manage students and guardians"),
    ("students.enroll", "Enroll and place students"),
    ("students.documents", "Manage student documents"),
    ("portal.dashboard", "Access role dashboard"),
    ("finance.read", "View finance information"),
    ("finance.manage", "Manage finance information"),
    ("students.self", "Access own student profile"),
    ("guardian.self", "Access own guardian portal"),
    ("account.activate", "Activate a provisioned account"),
    ("accounts.manage", "Provision and manage portal accounts"),
]

ROLES = {
    "school_admin": ("School Administrator", [p[0] for p in TENANT_PERMISSIONS]),
    "registrar": ("Registrar", ["portal.dashboard", "students.read", "students.manage", "students.enroll", "students.documents", "accounts.manage"]),
    "bursar": ("Bursar / Finance Officer", ["portal.dashboard", "finance.read", "finance.manage"]),
    "teacher": ("Teacher", ["portal.dashboard", "school.structure.read", "students.read"]),
    "guardian": ("Guardian", ["portal.dashboard", "guardian.self"]),
    "student": ("Student", ["portal.dashboard", "students.self"]),
}

DOCUMENT_TYPES = [
    ("birth_certificate", "Birth Certificate", False),
    ("previous_school_report", "Previous School Report", False),
    ("transfer_certificate", "Transfer Certificate", False),
]


async def create_tenant(payload: CreateTenantRequest) -> TenantResponse:
    pool = get_pool()
    tenant_id = uuid4()
    host = f"{payload.slug}.localhost" if settings.app_env.lower() != "production" else f"{payload.slug}.{settings.root_domain}"
    tenant_status = "active" if payload.database_mode == "shared" else "provisioning"

    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT 1 FROM tenants WHERE slug=%s OR EXISTS (SELECT 1 FROM tenant_domains WHERE hostname=%s) LIMIT 1",
                    (payload.slug, host),
                )
                if await cur.fetchone():
                    raise HTTPException(status_code=409, detail="Tenant slug is already in use")

                await cur.execute(
                    "INSERT INTO tenants (id,name,slug,status,database_mode) VALUES (%s,%s,%s,%s,%s)",
                    (str(tenant_id), payload.name.strip(), payload.slug, tenant_status, payload.database_mode),
                )
                await cur.execute(
                    "INSERT INTO tenant_domains (id,tenant_id,hostname,is_primary,verified_at) VALUES (%s,%s,%s,1,NOW())",
                    (str(uuid4()), str(tenant_id), host),
                )

                role_ids = {code: str(uuid4()) for code in ROLES}
                role_values = []
                for code, (name, _) in ROLES.items():
                    role_values.extend([role_ids[code], str(tenant_id), code, name])
                placeholders = ",".join(["(%s,%s,%s,%s,1)"] * len(ROLES))
                await cur.execute(
                    f"INSERT INTO tenant_roles (id,tenant_id,code,name,is_system) VALUES {placeholders}",
                    tuple(role_values),
                )

                permission_ids = {}
                for code, name in TENANT_PERMISSIONS:
                    pid = str(uuid4())
                    permission_ids[code] = pid
                    await cur.execute(
                        "INSERT INTO tenant_permissions (id,tenant_id,code,name) VALUES (%s,%s,%s,%s)",
                        (pid, str(tenant_id), code, name),
                    )

                for role_code, (_, permissions) in ROLES.items():
                    for permission_code in permissions:
                        await cur.execute(
                            "INSERT INTO tenant_role_permissions (role_id,permission_id) VALUES (%s,%s)",
                            (role_ids[role_code], permission_ids[permission_code]),
                        )

                for code, name, required in DOCUMENT_TYPES:
                    await cur.execute(
                        "INSERT INTO student_document_types (id,tenant_id,code,name,is_required) VALUES (%s,%s,%s,%s,%s)",
                        (str(uuid4()), str(tenant_id), code, name, required),
                    )

                await cur.execute(
                    "INSERT INTO identity_audit_log (actor_type,action,target_type,target_id,tenant_id) VALUES ('platform','tenant.create','tenant',%s,%s)",
                    (str(tenant_id), str(tenant_id)),
                )
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise

    return TenantResponse(
        id=tenant_id,
        name=payload.name.strip(),
        slug=payload.slug,
        status=tenant_status,
        database_mode=payload.database_mode,
        host=host,
    )


async def list_tenants() -> list[TenantResponse]:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id,name,slug,status,database_mode FROM tenants ORDER BY name")
            rows = await cur.fetchall()
    return [
        TenantResponse(
            id=UUID(str(row[0])),
            name=row[1],
            slug=row[2],
            status=row[3],
            database_mode=row[4],
            host=f"{row[2]}.localhost" if settings.app_env.lower() != "production" else f"{row[2]}.{settings.root_domain}",
        )
        for row in rows
    ]
