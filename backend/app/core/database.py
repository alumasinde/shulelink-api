from pathlib import Path
import asyncio
import ssl
from contextvars import ContextVar
import aiomysql
from app.core.config import settings
_pool: aiomysql.Pool | None = None
_pool_lock = asyncio.Lock()
_request_pool: ContextVar[aiomysql.Pool | None] = ContextVar("shulelink_request_pool", default=None)
def _ssl_context() -> ssl.SSLContext | None:
    if not settings.db_ssl_ca:return None
    context=ssl.create_default_context(cafile=settings.db_ssl_ca)
    if not settings.db_ssl_verify:context.check_hostname=False; context.verify_mode=ssl.CERT_NONE
    return context
async def initialize_database() -> None:
    global _pool
    if _pool is not None:return
    async with _pool_lock:
        if _pool is not None:return
        # aiomysql 0.2.0 exposes connect_timeout but not PyMySQL's read/write timeout kwargs.
        kwargs=dict(host=settings.db_host,port=settings.db_port,user=settings.db_user,password=settings.db_password,db=settings.db_name,minsize=settings.db_pool_min_size,maxsize=settings.db_pool_max_size,pool_recycle=settings.db_pool_recycle_seconds,connect_timeout=settings.db_connect_timeout_seconds,autocommit=True,charset="utf8mb4",use_unicode=True)
        ssl_context=_ssl_context()
        if ssl_context is not None:kwargs["ssl"]=ssl_context
        _pool=await aiomysql.create_pool(**kwargs)
def get_central_pool() -> aiomysql.Pool:
    if _pool is None:raise RuntimeError("Database is not initialized")
    return _pool
def get_pool() -> aiomysql.Pool:return _request_pool.get() or get_central_pool()
def set_request_pool(pool:aiomysql.Pool):return _request_pool.set(pool)
def reset_request_pool(token)->None:_request_pool.reset(token)
def get_pool_stats()->dict[str,int]:
    pool=get_central_pool(); return {"size":pool.size,"free":pool.freesize,"in_use":max(pool.size-pool.freesize,0),"max":pool.maxsize}
async def close_database()->None:
    global _pool
    async with _pool_lock:
        if _pool is not None:_pool.close(); await _pool.wait_closed(); _pool=None
async def ping_database()->bool:
    if _pool is None:return False
    try:
        async with _pool.acquire() as connection:
            async with connection.cursor() as cursor:await cursor.execute("SELECT 1"); await cursor.fetchone()
        return True
    except Exception:return False
async def run_migrations()->None:
    pool=get_central_pool(); migrations_dir=Path(__file__).resolve().parents[2]/"database"/"migrations"; files=sorted(migrations_dir.glob("*.sql"))
    async with pool.acquire() as connection:
        lock_acquired=False
        try:
            async with connection.cursor() as cursor:
                await cursor.execute("SELECT GET_LOCK('shulelink:schema-migrations', 60)"); lock_acquired=(await cursor.fetchone())[0]==1
                if not lock_acquired:raise RuntimeError("Timed out waiting for the database migration lock")
                await cursor.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version BIGINT UNSIGNED NOT NULL PRIMARY KEY, filename VARCHAR(255) NOT NULL, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE KEY uq_schema_migrations_filename (filename)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;")
                await cursor.execute("SELECT version FROM schema_migrations"); applied={row[0] for row in await cursor.fetchall()}; seen_versions:set[int]=set()
                for path in files:
                    version=int(path.name.split("_",1)[0])
                    # An applied migration is immutable history. Skip it before duplicate-version validation.
                    if version in applied:continue
                    if version in seen_versions:raise RuntimeError(f"Duplicate unapplied migration version detected: {version}")
                    seen_versions.add(version)
                    sql=path.read_text(encoding="utf-8").strip()
                    if not sql:continue
                    await cursor.execute(sql); await cursor.execute("INSERT INTO schema_migrations (version,filename) VALUES (%s,%s)",(version,path.name)); applied.add(version)
        finally:
            if lock_acquired:
                async with connection.cursor() as cursor:await cursor.execute("SELECT RELEASE_LOCK('shulelink:schema-migrations')")
