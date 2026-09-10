from pathlib import Path
import asyncio
import hashlib
import ssl
from contextvars import ContextVar

import aiomysql
from pymysql.constants import CLIENT

from app.core.config import settings

_pool: aiomysql.Pool | None = None
_pool_lock = asyncio.Lock()
_request_pool: ContextVar[aiomysql.Pool | None] = ContextVar("shulelink_request_pool", default=None)


def _ssl_context() -> ssl.SSLContext | None:
    if not settings.db_ssl_ca:
        return None
    context = ssl.create_default_context(cafile=settings.db_ssl_ca)
    if not settings.db_ssl_verify:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context


def _connection_kwargs(*, multi_statements: bool = False) -> dict:
    kwargs = dict(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        db=settings.db_name,
        connect_timeout=settings.db_connect_timeout_seconds,
        autocommit=True,
        charset="utf8mb4",
        use_unicode=True,
    )
    if multi_statements:
        kwargs["client_flag"] = CLIENT.MULTI_STATEMENTS
    ssl_context = _ssl_context()
    if ssl_context is not None:
        kwargs["ssl"] = ssl_context
    return kwargs


async def initialize_database() -> None:
    global _pool
    if _pool is not None:
        return
    async with _pool_lock:
        if _pool is not None:
            return
        kwargs = _connection_kwargs()
        kwargs.update(
            minsize=settings.db_pool_min_size,
            maxsize=settings.db_pool_max_size,
            pool_recycle=settings.db_pool_recycle_seconds,
        )
        _pool = await aiomysql.create_pool(**kwargs)


def get_central_pool() -> aiomysql.Pool:
    if _pool is None:
        raise RuntimeError("Database is not initialized")
    return _pool


def get_pool() -> aiomysql.Pool:
    return _request_pool.get() or get_central_pool()


def set_request_pool(pool: aiomysql.Pool):
    return _request_pool.set(pool)


def reset_request_pool(token) -> None:
    _request_pool.reset(token)


def get_pool_stats() -> dict[str, int]:
    pool = get_central_pool()
    return {
        "size": pool.size,
        "free": pool.freesize,
        "in_use": max(pool.size - pool.freesize, 0),
        "max": pool.maxsize,
    }


async def close_database() -> None:
    global _pool
    async with _pool_lock:
        if _pool is not None:
            _pool.close()
            await _pool.wait_closed()
            _pool = None


async def ping_database() -> bool:
    if _pool is None:
        return False
    try:
        async with _pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute("SELECT 1")
                await cursor.fetchone()
        return True
    except Exception:
        return False


async def _ensure_migration_metadata(cursor) -> None:
    await cursor.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version BIGINT UNSIGNED NOT NULL, "
        "filename VARCHAR(255) NOT NULL, "
        "checksum CHAR(64) NULL, "
        "applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, "
        "PRIMARY KEY (filename), "
        "KEY ix_schema_migrations_version (version)"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"
    )
    await cursor.nextset()

    await cursor.execute(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME='schema_migrations'",
        (settings.db_name,),
    )
    columns = {row[0] for row in await cursor.fetchall()}
    if "checksum" not in columns:
        await cursor.execute(
            "ALTER TABLE schema_migrations ADD COLUMN checksum CHAR(64) NULL AFTER filename"
        )
        await cursor.nextset()

    await cursor.execute(
        "SELECT COLUMN_NAME FROM information_schema.STATISTICS "
        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME='schema_migrations' "
        "AND INDEX_NAME='PRIMARY' ORDER BY SEQ_IN_INDEX",
        (settings.db_name,),
    )
    primary_columns = [row[0] for row in await cursor.fetchall()]
    if primary_columns == ["version"]:
        await cursor.execute(
            "ALTER TABLE schema_migrations DROP PRIMARY KEY, "
            "ADD PRIMARY KEY (filename), "
            "ADD KEY ix_schema_migrations_version (version)"
        )
        await cursor.nextset()


async def run_migrations() -> None:
    migrations_dir = Path(__file__).resolve().parents[2] / "database" / "migrations"
    files = sorted(migrations_dir.glob("*.sql"), key=lambda path: (int(path.name.split("_", 1)[0]), path.name))
    connection = await aiomysql.connect(**_connection_kwargs(multi_statements=True))
    try:
        lock_acquired = False
        async with connection.cursor() as cursor:
            try:
                await cursor.execute("SELECT GET_LOCK('shulelink:schema-migrations', 60)")
                lock_acquired = (await cursor.fetchone())[0] == 1
                if not lock_acquired:
                    raise RuntimeError("Timed out waiting for the database migration lock")

                await _ensure_migration_metadata(cursor)
                await cursor.execute("SELECT filename,checksum FROM schema_migrations")
                applied = {row[0]: row[1] for row in await cursor.fetchall()}

                for path in files:
                    filename = path.name
                    sql = path.read_text(encoding="utf-8").strip()
                    if not sql:
                        continue
                    version = int(filename.split("_", 1)[0])
                    checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()

                    if filename in applied:
                        recorded_checksum = applied[filename]
                        if recorded_checksum and recorded_checksum != checksum:
                            raise RuntimeError(
                                f"Applied migration was modified: {filename}"
                            )
                        if not recorded_checksum:
                            await cursor.execute(
                                "UPDATE schema_migrations SET checksum=%s WHERE filename=%s",
                                (checksum, filename),
                            )
                        continue

                    await cursor.execute(sql)
                    while await cursor.nextset():
                        pass

                    await cursor.execute(
                        "INSERT INTO schema_migrations (version,filename,checksum) VALUES (%s,%s,%s)",
                        (version, filename, checksum),
                    )
                    applied[filename] = checksum
            finally:
                if lock_acquired:
                    await cursor.execute("SELECT RELEASE_LOCK('shulelink:schema-migrations')")
    finally:
        connection.close()
        await connection.ensure_closed()
