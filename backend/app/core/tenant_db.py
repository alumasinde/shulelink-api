from uuid import UUID
import ssl
import aiomysql
from fastapi import HTTPException
from app.core.config import settings
from app.core.crypto import decrypt_secret
from app.core.database import get_central_pool
_pools:dict[str,aiomysql.Pool]={}
def _ssl_context():
    if not settings.db_ssl_ca:return None
    context=ssl.create_default_context(cafile=settings.db_ssl_ca)
    if not settings.db_ssl_verify:context.check_hostname=False; context.verify_mode=ssl.CERT_NONE
    return context
async def get_tenant_pool(tenant_id:UUID)->aiomysql.Pool:
    central=get_central_pool()
    async with central.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT database_mode,database_host,database_port,database_name,database_user,database_password_encrypted,status FROM tenants WHERE id=%s",(str(tenant_id),)); row=await cur.fetchone()
    if not row or row[6]!="active":raise HTTPException(404,"Tenant not found or inactive")
    if row[0]=="shared":return central
    if not all(row[1:6]):raise HTTPException(503,"Dedicated tenant database is not provisioned")
    key=str(tenant_id)
    if key in _pools:return _pools[key]
    try:password=decrypt_secret(row[5])
    except Exception as exc:raise HTTPException(503,"Dedicated tenant database credentials are unavailable") from exc
    kwargs=dict(host=row[1],port=int(row[2]),db=row[3],user=row[4],password=password,minsize=settings.db_pool_min_size,maxsize=settings.db_pool_max_size,pool_recycle=settings.db_pool_recycle_seconds,connect_timeout=settings.db_connect_timeout_seconds,read_timeout=settings.db_read_timeout_seconds,write_timeout=settings.db_write_timeout_seconds,autocommit=True,charset="utf8mb4",use_unicode=True)
    ssl_context=_ssl_context()
    if ssl_context is not None:kwargs["ssl"]=ssl_context
    pool=await aiomysql.create_pool(**kwargs); _pools[key]=pool; return pool
async def close_tenant_pools():
    for pool in list(_pools.values()):pool.close(); await pool.wait_closed()
    _pools.clear()
