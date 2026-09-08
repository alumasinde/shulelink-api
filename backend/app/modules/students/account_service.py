from datetime import datetime, timezone
from uuid import UUID, uuid4
import secrets

from fastapi import HTTPException

from app.core.database import get_pool
from app.core.security import hash_password
from app.modules.auth.access import create_activation


async def _create_account(tenant_id: UUID, first_name: str, last_name: str, role_code: str, purpose: str, email: str | None, login_identifier: str | None):
    pool = get_pool()
    user_id = uuid4()
    placeholder_password = hash_password(secrets.token_urlsafe(48))
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                await cur.execute("SELECT id FROM tenant_roles WHERE tenant_id=%s AND code=%s", (str(tenant_id), role_code))
                role = await cur.fetchone()
                if not role:
                    raise HTTPException(422, f"Role {role_code} is not configured for this school")
                if email:
                    await cur.execute("SELECT 1 FROM tenant_users WHERE email=%s", (email.lower().strip(),))
                    if await cur.fetchone():
                        raise HTTPException(409, "An account with that email already exists")
                if login_identifier:
                    await cur.execute("SELECT 1 FROM tenant_users WHERE login_identifier=%s", (login_identifier.lower().strip(),))
                    if await cur.fetchone():
                        raise HTTPException(409, "That login identifier is already in use")
                await cur.execute("INSERT INTO tenant_users (id,email,login_identifier,first_name,last_name,password_hash,status) VALUES (%s,%s,%s,%s,%s,%s,'active')", (str(user_id), email.lower().strip() if email else None, login_identifier.lower().strip() if login_identifier else None, first_name.strip(), last_name.strip(), placeholder_password))
                membership_id = uuid4()
                await cur.execute("INSERT INTO tenant_memberships (id,tenant_id,tenant_user_id,status,joined_at) VALUES (%s,%s,%s,'active',NOW())", (str(membership_id), str(tenant_id), str(user_id)))
                await cur.execute("INSERT INTO tenant_membership_roles (membership_id,role_id) VALUES (%s,%s)", (str(membership_id), str(role[0])))
                await conn.commit()
        except Exception:
            await conn.rollback()
            raise
    token, expires = await create_activation(tenant_id, user_id, purpose)
    return user_id, token, expires


async def provision_guardian_account(tenant_id: UUID, guardian_id: UUID, email: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT first_name,last_name,tenant_user_id FROM guardians WHERE id=%s AND tenant_id=%s", (str(guardian_id), str(tenant_id)))
            row = await cur.fetchone()
            if not row:
                raise HTTPException(404, "Guardian not found")
            if row[2]:
                raise HTTPException(409, "Guardian already has a portal account")
    user_id, token, expires = await _create_account(tenant_id, row[0], row[1], "guardian", "guardian", email, None)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("UPDATE guardians SET tenant_user_id=%s WHERE id=%s AND tenant_id=%s AND tenant_user_id IS NULL", (str(user_id), str(guardian_id), str(tenant_id)))
            if cur.rowcount != 1:
                raise HTTPException(409, "Guardian account could not be linked")
            await cur.execute("INSERT INTO identity_audit_log (actor_type,tenant_id,action,target_type,target_id) VALUES ('tenant',%s,'guardian.account.provision','guardian',%s)", (str(tenant_id), str(guardian_id)))
    return {"guardian_id": guardian_id, "user_id": user_id, "email": email.lower().strip(), "login_identifier": email.lower().strip(), "activation_token": token, "activation_expires_at": expires}


async def provision_student_account(tenant_id: UUID, student_id: UUID, email: str | None = None):
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT first_name,last_name,admission_number,tenant_user_id FROM students WHERE id=%s AND tenant_id=%s", (str(student_id), str(tenant_id)))
            row = await cur.fetchone()
            if not row:
                raise HTTPException(404, "Student not found")
            if row[3]:
                raise HTTPException(409, "Student already has a portal account")
    identifier = f"student-{row[2]}".lower()
    synthetic_email = email.lower().strip() if email else f"{identifier}@student.shulelink.local"
    user_id, token, expires = await _create_account(tenant_id, row[0], row[1], "student", "student", synthetic_email, identifier)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("UPDATE students SET tenant_user_id=%s WHERE id=%s AND tenant_id=%s AND tenant_user_id IS NULL", (str(user_id), str(student_id), str(tenant_id)))
            if cur.rowcount != 1:
                raise HTTPException(409, "Student account could not be linked")
            await cur.execute("INSERT INTO identity_audit_log (actor_type,tenant_id,action,target_type,target_id) VALUES ('tenant',%s,'student.account.provision','student',%s)", (str(tenant_id), str(student_id)))
    return {"student_id": student_id, "user_id": user_id, "email": synthetic_email, "login_identifier": identifier, "activation_token": token, "activation_expires_at": expires}


async def _account_status(tenant_id: UUID, user_id: UUID, account_type: str):
    pool = get_pool()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id,email,login_identifier,status FROM tenant_users WHERE id=%s LIMIT 1", (str(user_id),))
            user = await cur.fetchone()
            if not user:
                raise HTTPException(404, "Portal account not found")
            await cur.execute("SELECT expires_at,consumed_at,created_at FROM account_activation_tokens WHERE tenant_id=%s AND tenant_user_id=%s ORDER BY created_at DESC LIMIT 1", (str(tenant_id), str(user_id)))
            token = await cur.fetchone()
    if not token:
        state = "active"
    elif token[1] is not None:
        state = "active"
    elif token[0] <= now:
        state = "expired"
    else:
        state = "pending"
    return {"account_type": account_type, "user_id": user[0], "email": user[1], "login_identifier": user[2], "status": state, "user_status": user[3], "activation_expires_at": token[0] if token and token[1] is None else None}


async def get_guardian_account_status(tenant_id: UUID, guardian_id: UUID):
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT tenant_user_id FROM guardians WHERE id=%s AND tenant_id=%s", (str(guardian_id), str(tenant_id)))
            row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Guardian not found")
    if not row[0]:
        return {"account_type": "guardian", "status": "not_created", "guardian_id": guardian_id}
    result = await _account_status(tenant_id, UUID(str(row[0])), "guardian")
    result["guardian_id"] = guardian_id
    return result


async def get_student_account_status(tenant_id: UUID, student_id: UUID):
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT tenant_user_id FROM students WHERE id=%s AND tenant_id=%s", (str(student_id), str(tenant_id)))
            row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Student not found")
    if not row[0]:
        return {"account_type": "student", "status": "not_created", "student_id": student_id}
    result = await _account_status(tenant_id, UUID(str(row[0])), "student")
    result["student_id"] = student_id
    return result


async def _resend_activation(tenant_id: UUID, user_id: UUID, purpose: str):
    pool = get_pool()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT email,status FROM tenant_users WHERE id=%s", (str(user_id),))
            user = await cur.fetchone()
            if not user:
                raise HTTPException(404, "Portal account not found")
            if user[1] != "active":
                raise HTTPException(409, "Portal account is not active")
            await cur.execute("UPDATE account_activation_tokens SET consumed_at=%s WHERE tenant_id=%s AND tenant_user_id=%s AND consumed_at IS NULL", (now, str(tenant_id), str(user_id)))
    token, expires = await create_activation(tenant_id, user_id, purpose)
    return {"user_id": user_id, "email": user[0], "activation_token": token, "activation_expires_at": expires}


async def resend_guardian_activation(tenant_id: UUID, guardian_id: UUID):
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT tenant_user_id FROM guardians WHERE id=%s AND tenant_id=%s", (str(guardian_id), str(tenant_id)))
            row = await cur.fetchone()
    if not row or not row[0]:
        raise HTTPException(404, "Guardian portal account not found")
    return await _resend_activation(tenant_id, UUID(str(row[0])), "guardian")


async def resend_student_activation(tenant_id: UUID, student_id: UUID):
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT tenant_user_id FROM students WHERE id=%s AND tenant_id=%s", (str(student_id), str(tenant_id)))
            row = await cur.fetchone()
    if not row or not row[0]:
        raise HTTPException(404, "Student portal account not found")
    return await _resend_activation(tenant_id, UUID(str(row[0])), "student")
