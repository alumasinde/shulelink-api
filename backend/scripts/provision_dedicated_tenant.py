"""Provision and migrate a tenant into its dedicated MySQL database."""
import argparse
import asyncio
from pathlib import Path
import secrets
import string
import aiomysql
from app.core.config import settings
from app.core.crypto import encrypt_secret
from app.core.database import get_central_pool, initialize_database

EXCLUDED_TENANT_COPY_TABLES={"tenants","tenant_domains","tenant_users","tenant_membership_roles","tenant_role_permissions","tenant_access_sessions","auth_sessions","auth_login_throttles","password_reset_tokens","mfa_factors","mfa_challenges","mfa_recovery_codes","schema_migrations"}
CENTRAL_ONLY_MIGRATIONS={"0021_curriculum_management.sql"}

def quote(value:str)->str: return "'"+value.replace("'","''")+"'"
def identifier(value:str)->str: return "`"+value.replace("`","``")+"`"
def random_password()->str:
    alphabet=string.ascii_letters+string.digits+"-_"
    return "".join(secrets.choice(alphabet) for _ in range(40))

async def execute_migrations(conn):
    directory=Path(__file__).resolve().parents[1]/"database"/"migrations"
    async with conn.cursor() as cur:
        await cur.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version BIGINT UNSIGNED NOT NULL PRIMARY KEY, filename VARCHAR(255) NOT NULL, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE KEY uq_schema_migrations_filename (filename)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;")
        await cur.execute("SELECT version FROM schema_migrations")
        applied={r[0] for r in await cur.fetchall()}
        for path in sorted(directory.glob("*.sql")):
            version=int(path.name.split("_",1)[0])
            if version in applied or path.name in CENTRAL_ONLY_MIGRATIONS: continue
            sql=path.read_text(encoding="utf-8").strip()
            if sql:
                await cur.execute(sql); await cur.execute("INSERT INTO schema_migrations (version,filename) VALUES (%s,%s)",(version,path.name))
        # Record skipped central-only migrations so provisioning remains idempotent and
        # future migration runs do not repeatedly inspect them.
        for name in CENTRAL_ONLY_MIGRATIONS:
            version=int(name.split("_",1)[0])
            if version not in applied: await cur.execute("INSERT INTO schema_migrations (version,filename) VALUES (%s,%s)",(version,name))

async def copy_rows(source,target,table,where,params):
    async with source.cursor() as src:
        await src.execute(f"SELECT * FROM {identifier(table)} WHERE {where}",params)
        rows=await src.fetchall()
        if not rows:return 0
        columns=[d[0] for d in src.description]
    query=f"INSERT INTO {identifier(table)} ({','.join(identifier(c) for c in columns)}) VALUES ({','.join(['%s']*len(columns))})"
    async with target.cursor() as dst: await dst.executemany(query,rows)
    return len(rows)

async def provision(tenant_id:str):
    if not all((settings.db_provisioner_host,settings.db_provisioner_user,settings.db_provisioner_password)): raise RuntimeError("DB_PROVISIONER_HOST/USER/PASSWORD must be configured")
    await initialize_database(); central=get_central_pool()
    async with central.acquire() as source:
        async with source.cursor() as cur:
            await cur.execute("SELECT id,name,slug,status,database_mode,database_password_encrypted FROM tenants WHERE id=%s",(tenant_id,)); tenant=await cur.fetchone()
            if not tenant: raise RuntimeError("Tenant not found")
            if tenant[4]!="dedicated": raise RuntimeError("Tenant database_mode must be dedicated")
            if tenant[5]: raise RuntimeError("Dedicated database credentials already exist; refusing to overwrite them")
    slug=tenant[2]; db_name=f"shulelink_{slug[:42]}_{tenant_id.replace('-','')[:8]}"; db_user=f"sl_{slug[:20]}_{tenant_id.replace('-','')[:8]}"[:32]; db_password=random_password(); host=settings.db_provisioner_host; port=settings.db_provisioner_port; account_host=settings.db_provisioner_tenant_host
    admin=await aiomysql.connect(host=host,port=port,user=settings.db_provisioner_user,password=settings.db_provisioner_password,db=None,connect_timeout=settings.db_connect_timeout_seconds,autocommit=True)
    try:
        async with admin.cursor() as cur:
            await cur.execute(f"CREATE DATABASE IF NOT EXISTS {identifier(db_name)} CHARACTER SET utf8mb4 COLLATE=utf8mb4_unicode_ci")
            await cur.execute(f"CREATE USER IF NOT EXISTS {quote(db_user)}@{quote(account_host)} IDENTIFIED BY {quote(db_password)}")
            await cur.execute(f"ALTER USER {quote(db_user)}@{quote(account_host)} IDENTIFIED BY {quote(db_password)}")
            await cur.execute(f"GRANT ALL PRIVILEGES ON {identifier(db_name)}.* TO {quote(db_user)}@{quote(account_host)}")
    finally: admin.close()
    target=await aiomysql.connect(host=host,port=port,user=db_user,password=db_password,db=db_name,connect_timeout=settings.db_connect_timeout_seconds,autocommit=True)
    try:
        await execute_migrations(target)
        async with target.cursor() as cur:
            await cur.execute("SET FOREIGN_KEY_CHECKS=0")
            await cur.execute("INSERT INTO tenants (id,name,slug,status,database_mode) VALUES (%s,%s,%s,%s,'dedicated')",tenant[:4])
        async with central.acquire() as source:
            await copy_rows(source,target,"tenant_users","id IN (SELECT tenant_user_id FROM tenant_memberships WHERE tenant_id=%s)",(tenant_id,))
            async with source.cursor() as cur:
                await cur.execute("SELECT DISTINCT table_name FROM information_schema.columns WHERE table_schema=%s AND column_name='tenant_id' ORDER BY table_name",(settings.db_name,)); tables=[r[0] for r in await cur.fetchall() if r[0] not in EXCLUDED_TENANT_COPY_TABLES]
            for table in tables: await copy_rows(source,target,table,"tenant_id=%s",(tenant_id,))
            await copy_rows(source,target,"tenant_membership_roles","membership_id IN (SELECT id FROM tenant_memberships WHERE tenant_id=%s)",(tenant_id,))
            await copy_rows(source,target,"tenant_role_permissions","role_id IN (SELECT id FROM tenant_roles WHERE tenant_id=%s)",(tenant_id,))
            async with source.cursor() as cur:
                await cur.execute("SELECT id,tenant_id,hostname,is_primary,verified_at,created_at FROM tenant_domains WHERE tenant_id=%s",(tenant_id,)); domains=await cur.fetchall()
            if domains:
                async with target.cursor() as cur: await cur.executemany("INSERT INTO tenant_domains (id,tenant_id,hostname,is_primary,verified_at,created_at) VALUES (%s,%s,%s,%s,%s,%s)",domains)
        async with target.cursor() as cur: await cur.execute("SET FOREIGN_KEY_CHECKS=1")
        async with central.acquire() as conn:
            async with conn.cursor() as cur: await cur.execute("UPDATE tenants SET database_host=%s,database_port=%s,database_name=%s,database_user=%s,database_password_encrypted=%s,status='active' WHERE id=%s",(host,port,db_name,db_user,encrypt_secret(db_password),tenant_id))
        print(f"Dedicated tenant database provisioned: {db_name} ({db_user})")
    except Exception:
        try:
            async with target.cursor() as cur: await cur.execute("SET FOREIGN_KEY_CHECKS=1")
        except Exception: pass
        raise
    finally: target.close()

if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("tenant_id"); args=parser.parse_args(); asyncio.run(provision(args.tenant_id))
