import asyncio
import ssl
from uuid import UUID

import aiomysql
from fastapi import HTTPException

from app.core.config import settings
from app.core.crypto import decrypt_secret
from app.core.database import get_central_pool

_pools: dict[str, aiomysql.Pool] = {}
_pool_lock = asyncio.Lock()


def _ssl_context() -> ssl.SSLContext | None:
    if not settings.db_ssl_ca:
        return None
    context = ssl.create_default_context(cafile=settings.db_ssl_ca)
    if not settings.db_ssl_verify:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context


async def get_tenant_pool(tenant_id: UUID) -> aiomysql.Pool:
    central = get_central_pool()
    async with central.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT database_mode,database_host,database_port,database_name,database_user,database_password_encrypted,status "
                "FROM tenants WHERE id=%s",
                (str(tenant_id),),
            )
            row = await cur.fetchone()

    if not row or row[6] != "active":
        raise HTTPException(404, "Tenant not found or inactive")
    if row[0] == "shared":
        return central
    if not all(row[1:6]):
        raise HTTPException(503, "Dedicated tenant database is not provisioned")

    key = str(tenant_id)
    async with _pool_lock:
        existing = _pools.get(key)
        if existing is not None:
            return existing
        if len(_pools) >= settings.db_max_dedicated_tenant_pools:
            raise HTTPException(
                503,
                "Dedicated tenant database capacity is temporarily exhausted; please retry later",
            )

        try:
            password = decrypt_secret(row[5])
        except Exception as exc:
            raise HTTPException(503, "Dedicated tenant database credentials are unavailable") from exc

        # Keep kwargs compatible with aiomysql 0.2.0; it accepts connect_timeout
        # but not PyMySQL's read/write timeout kwargs.
        kwargs = dict(
            host=row[1],
            port=int(row[2]),
            db=row[3],
            user=row[4],
            password=password,
            minsize=settings.db_tenant_pool_min_size,
            maxsize=settings.db_tenant_pool_max_size,
            pool_recycle=settings.db_pool_recycle_seconds,
            connect_timeout=settings.db_connect_timeout_seconds,
            autocommit=True,
            charset="utf8mb4",
            use_unicode=True,
        )
        ssl_context = _ssl_context()
        if ssl_context is not None:
            kwargs["ssl"] = ssl_context

        pool = await aiomysql.create_pool(**kwargs)
        _pools[key] = pool
        return pool


def get_tenant_pool_stats() -> dict[str, int]:
    return {
        "pools": len(_pools),
        "max_pools": settings.db_max_dedicated_tenant_pools,
        "connections": sum(pool.size for pool in _pools.values()),
        "in_use": sum(max(pool.size - pool.freesize, 0) for pool in _pools.values()),
        "max_connections": len(_pools) * settings.db_tenant_pool_max_size,
        "max_theoretical_connections": settings.max_theoretical_db_connections,
    }


async def close_tenant_pools() -> None:
    async with _pool_lock:
        pools = list(_pools.values())
        _pools.clear()
        for pool in pools:
            pool.close()
        for pool in pools:
            await pool.wait_closed()
