from pathlib import Path
import aiomysql

from app.core.config import settings

_pool: aiomysql.Pool | None = None


async def initialize_database() -> None:
    global _pool
    if _pool is not None:
        return
    _pool = await aiomysql.create_pool(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        db=settings.db_name,
        minsize=settings.db_pool_min_size,
        maxsize=settings.db_pool_max_size,
        autocommit=True,
        charset="utf8mb4",
    )


async def close_database() -> None:
    global _pool
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


async def run_migrations() -> None:
    if _pool is None:
        raise RuntimeError("Database is not initialized")

    migrations_dir = Path(__file__).resolve().parents[2] / "database" / "migrations"
    files = sorted(migrations_dir.glob("*.sql"))

    async with _pool.acquire() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version BIGINT UNSIGNED NOT NULL PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL,
                    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uq_schema_migrations_filename (filename)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """
            )
            await cursor.execute("SELECT version FROM schema_migrations")
            applied = {row[0] for row in await cursor.fetchall()}

            for path in files:
                version = int(path.name.split("_", 1)[0])
                if version in applied:
                    continue
                sql = path.read_text(encoding="utf-8").strip()
                if not sql:
                    continue
                await cursor.execute(sql)
                await cursor.execute(
                    "INSERT INTO schema_migrations (version, filename) VALUES (%s, %s)",
                    (version, path.name),
                )
