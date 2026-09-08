from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.core.config import settings
from app.core.database import get_pool
from app.core.mfa import (
    decrypt_totp_secret,
    encrypt_totp_secret,
    generate_recovery_codes,
    generate_totp_secret,
    hash_recovery_code,
    otpauth_uri,
    verify_totp,
)
from app.core.security import create_access_token, create_refresh_token, hash_password, hash_token, validate_password, verify_password
from app.modules.auth.email import send_password_reset_email


LOCK_AFTER_FAILURES = 5
LOCK_MINUTES = 15


def account_key(user_type: str, identifier: str) -> str:
    return hashlib.sha256(f"{user_type}:{identifier.strip().lower()}".encode()).hexdigest()


async def ensure_not_throttled(user_type: str, identifier: str) -> None:
    key = account_key(user_type, identifier)
    pool = get_pool()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT locked_until FROM auth_login_throttles WHERE account_key=%s LIMIT 1", (key,))
            row = await cur.fetchone()
    if row and row[0] and row[0] > now:
        raise HTTPException(status_code=429, detail="Too many authentication attempts. Try again later.")


async def record_login_failure(user_type: str, identifier: str) -> None:
    key = account_key(user_type, identifier)
    pool = get_pool()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT failed_attempts,first_failed_at FROM auth_login_throttles WHERE account_key=%s FOR UPDATE", (key,))
            row = await cur.fetchone()
            if not row or not row[1] or (now - row[1]).total_seconds() > 900:
                await cur.execute("INSERT INTO auth_login_throttles (account_key,user_type,failed_attempts,first_failed_at,locked_until) VALUES (%s,%s,1,%s,NULL) ON DUPLICATE KEY UPDATE failed_attempts=1,first_failed_at=VALUES(first_failed_at),locked_until=NULL", (key,user_type,now))
                return
            failures = int(row[0]) + 1
            locked_until = now + timedelta(minutes=LOCK_MINUTES) if failures >= LOCK_AFTER_FAILURES else None
            await cur.execute("UPDATE auth_login_throttles SET failed_attempts=%s,locked_until=%s WHERE account_key=%s", (failures,locked_until,key))


async def clear_login_throttle(user_type: str, identifier: str) -> None:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM auth_login_throttles WHERE account_key=%s", (account_key(user_type, identifier),))


async def issue_session(conn, user_type: str, user_id: UUID, tenant_id: UUID | None):
    session_id = uuid4()
    refresh_raw, refresh_hash, refresh_expires = create_refresh_token()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    await conn.cursor().execute(
        "INSERT INTO auth_sessions (id,user_type,user_id,tenant_id,refresh_token_hash,expires_at,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (str(session_id),user_type,str(user_id),str(tenant_id) if tenant_id else None,refresh_hash,refresh_expires.replace(tzinfo=None),now),
    )
    access, access_expires = create_access_token(user_id=str(user_id),user_type=user_type,tenant_id=str(tenant_id) if tenant_id else None,session_id=str(session_id))
    return access, refresh_raw, access_expires, session_id


async def create_mfa_challenge(user_type: str, user_id: UUID, tenant_id: UUID | None) -> UUID:
    challenge_id = uuid4()
    expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=settings.mfa_challenge_minutes)
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("INSERT INTO mfa_challenges (id,user_type,user_id,tenant_id,expires_at) VALUES (%s,%s,%s,%s,%s)", (str(challenge_id),user_type,str(user_id),str(tenant_id) if tenant_id else None,expires))
    return challenge_id


async def mfa_enabled(user_type: str, user_id: UUID) -> bool:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1 FROM mfa_factors WHERE user_type=%s AND user_id=%s AND factor_type='totp' AND enabled=1 LIMIT 1", (user_type,str(user_id)))
            return bool(await cur.fetchone())


async def verify_mfa_challenge(challenge_id: UUID, code: str):
    pool = get_pool()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id,user_type,user_id,tenant_id,expires_at,attempts,used_at FROM mfa_challenges WHERE id=%s LIMIT 1", (str(challenge_id),))
            challenge = await cur.fetchone()
            if not challenge or challenge[6] is not None or challenge[4] <= now or challenge[5] >= 5:
                raise HTTPException(status_code=401, detail="Invalid or expired MFA challenge")
            await cur.execute("SELECT id,secret_encrypted FROM mfa_factors WHERE user_type=%s AND user_id=%s AND factor_type='totp' AND enabled=1 LIMIT 1", (challenge[1],str(challenge[2])))
            factor = await cur.fetchone()
            if not factor:
                raise HTTPException(status_code=401, detail="MFA is not configured")
            valid = verify_totp(decrypt_totp_secret(factor[1]), code)
            if not valid:
                await cur.execute("SELECT id,used_at FROM mfa_recovery_codes WHERE factor_id=%s AND code_hash=%s LIMIT 1", (str(factor[0]),hash_recovery_code(code)))
                recovery = await cur.fetchone()
                valid = bool(recovery and recovery[1] is None)
                if valid:
                    await cur.execute("UPDATE mfa_recovery_codes SET used_at=%s WHERE id=%s", (now,str(recovery[0])))
            if not valid:
                await cur.execute("UPDATE mfa_challenges SET attempts=attempts+1 WHERE id=%s", (str(challenge_id),))
                raise HTTPException(status_code=401, detail="Invalid MFA code")
            await cur.execute("UPDATE mfa_challenges SET used_at=%s WHERE id=%s", (now,str(challenge_id)))
            access, refresh, expires, session_id = await issue_session(conn, challenge[1], UUID(str(challenge[2])), UUID(str(challenge[3])) if challenge[3] else None)
            await cur.execute("INSERT INTO identity_audit_log (actor_type,actor_id,tenant_id,action,target_type,target_id) VALUES (%s,%s,%s,'auth.mfa_login',%s,%s)", (challenge[1],str(challenge[2]),str(challenge[3]) if challenge[3] else None,challenge[1],str(challenge[2])))
            return access, refresh, expires, session_id


async def begin_mfa_enrollment(user_type: str, user_id: UUID, email: str):
    factor_id = uuid4()
    secret = generate_totp_secret()
    encrypted = encrypt_totp_secret(secret)
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("INSERT INTO mfa_factors (id,user_type,user_id,factor_type,secret_encrypted,enabled,verified_at) VALUES (%s,%s,%s,'totp',%s,0,NULL) ON DUPLICATE KEY UPDATE id=VALUES(id),secret_encrypted=VALUES(secret_encrypted),enabled=0,verified_at=NULL", (str(factor_id),user_type,str(user_id),encrypted))
    return factor_id, secret, otpauth_uri(secret, settings.mfa_issuer, email)


async def verify_mfa_enrollment(user_type: str, user_id: UUID, code: str) -> list[str]:
    pool = get_pool()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id,secret_encrypted FROM mfa_factors WHERE user_type=%s AND user_id=%s AND factor_type='totp' AND enabled=0 LIMIT 1", (user_type,str(user_id)))
            factor = await cur.fetchone()
            if not factor or not verify_totp(decrypt_totp_secret(factor[1]), code):
                raise HTTPException(status_code=400, detail="Invalid MFA verification code")
            await cur.execute("UPDATE mfa_factors SET enabled=1,verified_at=%s WHERE id=%s", (now,str(factor[0])))
            codes = generate_recovery_codes()
            await cur.execute("DELETE FROM mfa_recovery_codes WHERE factor_id=%s", (str(factor[0]),))
            for code_value in codes:
                await cur.execute("INSERT INTO mfa_recovery_codes (id,factor_id,code_hash) VALUES (%s,%s,%s)", (str(uuid4()),str(factor[0]),hash_recovery_code(code_value)))
            await cur.execute("INSERT INTO identity_audit_log (actor_type,actor_id,action,target_type,target_id) VALUES (%s,%s,'auth.mfa_enabled',%s,%s)", (user_type,str(user_id),user_type,str(user_id)))
            return codes


async def disable_mfa(user_type: str, user_id: UUID) -> None:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM mfa_factors WHERE user_type=%s AND user_id=%s", (user_type,str(user_id)))
            await cur.execute("INSERT INTO identity_audit_log (actor_type,actor_id,action,target_type,target_id) VALUES (%s,%s,'auth.mfa_disabled',%s,%s)", (user_type,str(user_id),user_type,str(user_id)))


async def mfa_status(user_type: str, user_id: UUID) -> dict:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT enabled,factor_type FROM mfa_factors WHERE user_type=%s AND user_id=%s LIMIT 1", (user_type,str(user_id)))
            row = await cur.fetchone()
    return {"enabled": bool(row and row[0]), "factor_type": row[1] if row else None}


async def request_password_reset(user_type: str, email: str) -> str | None:
    normalized = email.strip().lower()
    table = "platform_users" if user_type == "platform" else "tenant_users"
    pool = get_pool()
    token = None
    user_id = None
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"SELECT id,status FROM {table} WHERE email=%s LIMIT 1", (normalized,))
            row = await cur.fetchone()
            if row and row[1] == "active":
                user_id = UUID(str(row[0]))
                token = secrets.token_urlsafe(48)
                token_hash = hash_token(token)
                expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=settings.password_reset_minutes)
                await cur.execute("UPDATE password_reset_tokens SET used_at=NOW() WHERE user_type=%s AND user_id=%s AND used_at IS NULL", (user_type,str(user_id)))
                await cur.execute("INSERT INTO password_reset_tokens (id,user_type,user_id,token_hash,expires_at) VALUES (%s,%s,%s,%s,%s)", (str(uuid4()),user_type,str(user_id),token_hash,expires))
    if token and user_id:
        if settings.auth_reset_return_token:
            return token
        try:
            await send_password_reset_email(normalized, token)
        except Exception:
            # Do not expose delivery failures or whether the account exists.
            return None
    return None


async def confirm_password_reset(token: str, password: str) -> None:
    validate_password(password)
    token_hash = hash_token(token)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id,user_type,user_id,expires_at,used_at FROM password_reset_tokens WHERE token_hash=%s LIMIT 1", (token_hash,))
            row = await cur.fetchone()
            if not row or row[4] is not None or row[3] <= now:
                raise HTTPException(status_code=400, detail="Invalid or expired password reset token")
            table = "platform_users" if row[1] == "platform" else "tenant_users"
            password_hash = hash_password(password)
            await cur.execute(f"UPDATE {table} SET password_hash=%s WHERE id=%s", (password_hash,str(row[2])))
            await cur.execute("UPDATE password_reset_tokens SET used_at=%s WHERE id=%s", (now,str(row[0])))
            await cur.execute("UPDATE auth_sessions SET revoked_at=%s WHERE user_type=%s AND user_id=%s AND revoked_at IS NULL", (now,row[1],str(row[2])))
            await cur.execute("INSERT INTO identity_audit_log (actor_type,actor_id,action,target_type,target_id) VALUES (%s,%s,'auth.password_reset',%s,%s)", (row[1],str(row[2]),row[1],str(row[2])))
