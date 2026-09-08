from fastapi import APIRouter, Depends
from app.core.dependencies import require_tenant
from app.core.database import get_pool

router = APIRouter(prefix="/tenant", tags=["Tenant Context"])

@router.get("/context")
async def context(tenant_id = Depends(require_tenant)):
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id,name,slug,status,database_mode FROM tenants WHERE id=%s", (str(tenant_id),))
            row = await cur.fetchone()
    return {"success": True, "data": {"tenant": {"id": str(row[0]), "name": row[1], "slug": row[2], "status": row[3], "database_mode": row[4]}}}
