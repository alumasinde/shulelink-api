"""Provision and migrate a tenant into its dedicated MySQL database.

Run from backend/ after the central database is reachable. The application DB user
must not have CREATE USER/CREATE DATABASE; this script uses the separate provisioner
identity configured by DB_PROVISIONER_*.
"""

import argparse
import asyncio
from pathlib import Path
import secrets
import string

import aiomysql

from app.core.config import settings
from app.core.crypto import encrypt_secret
from app.core.database import get_central_pool, initialize_database


EXCLUDED_TENANT_COPY_TABLES = {
    "tenants", "tenant_users", "tenant_membership_roles", "tenant_role_permissions",
    "tenant_access_sessions", "auth_sessions", "auth_login_throttles", "password_reset_tokens",
    "mfa_factors", "mfa_challenges", "mfa_recovery_codes", "schema_migrations",
}


def quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def identifier(value: str) -> str:
    return "`" + value.replace("`", "``") + "`"


def random_password() -> str:
    alphabet = string.ascii_letters + string.digits + "-_"
    return "".join(secrets.choice(alphabet) for _ in range(40))


async def execute_migrations(conn) -> None:
    migrations_dir = Path(__file__).resolve().parents[1] / "database" / "migrations"
    async with conn.cursor() as cur:
        await cur.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version BIGINT UNSIGNED NOT NULL PRIMARY KEY, filename VARCHAR(255) NOT NULL, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE KEY uq_schema_migrations_filename (filename)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;")
        await cur.execute("SELECT version FROM schema_migrations")
        applied = {row[0] for row in await cur.fetchall()}
        for path in sorted(migrations_dir.glob("*.sql")):
            version = int(path.name.split("_", 1)[0])
            if version in applied: continue
            sql = path.read_text(encoding="utf-8").strip()
            if not sql: continue
            await cur.execute(sql)
            await cur.execute("INSERT INTO schema_migrations (version,filename) VALUES (%s,%s)", (version, path.name))


async def copy_rows(source, target, table: str, where: str, params: tuple) -> int:
    async with source.cursor() as src:
        await src.execute(f"SELECT * FROM {identifier(table)} WHERE {where}", params)
        rows = await src.fetchall()
        if not rows: return 0
        columns = [item[0] for item in src.description]
    placeholders = ",".join(["%s"] * len(columns))
    query = f"INSERT INTO {identifier(table)} ({','.join(identifier(c) for c in columns)}) VALUES ({placeholders})"
    async with target.cursor() as dst:
        await dst.executemany(query, rows)
    return len(rows)


async def provision(tenant_id: str) -> None:
    if not settings.db_provisioner_host or not settings.db_provisioner_user or not settings.db_provisioner_password:
        raise RuntimeError("DB_PROVISIONER_HOST/USER/PASSWORD must be configured")
    await initialize_database()
    central = get_central_pool()
    async with central.acquire() as source:
        async with source.cursor() as cur:
            await cur.execute("SELECT id,name,slug,status,database_mode FROM tenants WHERE id=%s", (tenant_id,))
            tenant = await cur.fetchone()
            if not tenant: raise RuntimeError("Tenant not found")
            if tenant[4] != "dedicated": raise RuntimeError("Tenant database_mode must be dedicated")
            await cur.execute("SELECT COUNT(*) FROM tenants WHERE id=%s AND database_password_encrypted IS NOT NULL", (tenant_id,))
            if (await cur.fetchone())[0]: raise RuntimeError("Dedicated database credentials already exist; refusing to overwrite them")

    slug = tenant[2]
    db_name = f"shulelink_{slug[:42]}_{tenant_id.replace('-', '')[:8]}"
    db_user = f"sl_{slug[:20]}_{tenant_id.replace('-', '')[:8]}"[:32]
    db_password = random_password()
    db_host = settings.db_provisioner_host
    db_port = settings.db_provisioner_port
    target_host = settings.db_provisioner_tenant_host

    admin = await aiomysql.connect(host=db_host, port=db_port, user=settings.db_provisioner_user, password=settings.db_provisioner_password, db=None, connect_timeout=settings.db_connect_timeout_seconds, autocommit=True)
    try:
        async with admin.cursor() as cur:
            await cur.execute(f"CREATE DATABASE IF NOT EXISTS {identifier(db_name)} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            await cur.execute(f"CREATE USER IF NOT EXISTS {quote(db_user)}@{quote(target_host)} IDENTIFIED BY {quote(db_password)}")
            await cur.execute(f"ALTER USER {quote(db_user)}@{quote(target_host)} IDENTIFIED BY {quote(db_password)}")
            await cur.execute(f"GRANT ALL PRIVILEGES ON {identifier(db_name)}.* TO {quote(db_user)}@{quote(target_host)}")
            await cur.execute("FLUSH PRIVILEGES")
    finally:
        admin.close()

    target = await aiomysql.connect(host=db_host, port=db_port, user=db_user, password=db_password, db=db_name, connect_timeout=settings.db_connect_timeout_seconds, autocommit=True)
    try:
        await execute_migrations(target)
        async with target.cursor() as cur:
            await cur.execute("SET FOREIGN_KEY_CHECKS=0")
            await cur.execute("INSERT INTO tenants (id,name,slug,status,database_mode) VALUES (%s,%s,%s,%s,'dedicated')", (tenant[0],tenant[1],tenant[2],tenant[3]))

        async with central.acquire() as source:
            await copy_rows(source, target, "tenant_users", "id IN (SELECT tenant_user_id FROM tenant_memberships WHERE tenant_id=%s)", (tenant_id,))
            tenant_tables = []
            async with source.cursor() as cur:
                await cur.execute("SELECT DISTINCT table_name FROM information_schema.columns WHERE table_schema=%s AND column_name='tenant_id' ORDER BY table_name", (settings.db_name,))
                tenant_tables = [row[0] for row in await cur.fetchall() if row[0] not in EXCLUDED_TENANT_COPY_TABLES]
            for table in tenant_tables:
                if table == "tenant_users": continue
                await copy_rows(source, target, table, "tenant_id=%s", (tenant_id,))
            await copy_rows(source, target, "tenant_membership_roles", "membership_id IN (SELECT id FROM tenant_memberships WHERE tenant_id=%s)", (tenant_id,))
            await copy_rows(source, target, "tenant_role_permissions", "role_id IN (SELECT id FROM tenant_roles WHERE tenant_id=%s)", (tenant_id,))
            async with source.cursor() as cur:
                await cur.execute("SELECT id,tenant_id,hostname,is_primary,verified_at,created_at FROM tenant_domains WHERE tenant_id=%s", (tenant_id,))
                domains = await cur.fetchall()
            async with target.cursor() as cur:
                if domains:
                    await cur.executemany("INSERT INTO tenant_domains (id,tenant_id,hostname,is_primary,verified_at,created_at) VALUES (%s,%s,%s,%s,%s,%s)", domains)

        async with target.cursor() as cur:
            await cur.execute("SET FOREIGN_KEY_CHECKS=1")

        async with central.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE tenants SET database_host=%s,database_port=%s,database_name=%s,database_user=%s,database_password_encrypted=%s,status='active' WHERE id=%s", (db_host,db_port,db_name,db_user,encrypt_secret(db_password),tenant_id))
        print(f"Dedicated tenant database provisioned: {db_name} ({db_user})")
    except Exception:
        try:
            async with target.cursor() as cur: await cur.execute("SET FOREIGN_KEY_CHECKS=1")
        except Exception: pass
        raise
    finally:
        target.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("tenant_id")
    args = parser.parse_args()
    asyncio.run(provision(args.tenant_id))
