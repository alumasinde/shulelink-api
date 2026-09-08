from uuid import UUID
import aiomysql
from fastapi import HTTPException
from app.core.database import get_pool

_pools: dict[str, aiomysql.Pool] = {}

async def get_tenant_pool(tenant_id: UUID) -> aiomysql.Pool:
    """Resolve the tenant database without allowing the request to choose a database directly.
    Shared tenants use the central pool. Dedicated tenants use their registered database target.
    Dedicated credential decryption/provisioning is intentionally isolated here so business modules
    never need to know how tenant databases are selected.
    """
    central = get_pool()
    async with central.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT database_mode,database_host,database_port,database_name,database_user,database_password_encrypted,status FROM tenants WHERE id=%s", (str(tenant_id),))
            row = await cur.fetchone()
    if not row or row[6] != "active":
        raise HTTPException(status_code=404, detail="Tenant not found or inactive")
    if row[0] == "shared":
        return central
    if not all(row[1:6]):
        raise HTTPException(status_code=503, detail="Dedicated tenant database is not provisioned")
    key = str(tenant_id)
    existing = _pools.get(key)
    if existing:
        return existing
    # The password field is expected to contain an application-encrypted secret once dedicated
    # database provisioning is enabled. Fail closed rather than treating it as plaintext.
    raise HTTPException(status_code=503, detail="Dedicated tenant database credentials are not provisioned")

async def close_tenant_pools() -> None:
    for pool in list(_pools.values()):
        pool.close()
        await pool.wait_closed()
    _pools.clear()
