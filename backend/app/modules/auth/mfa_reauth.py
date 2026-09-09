from uuid import UUID
from fastapi import HTTPException
from app.core.database import get_central_pool
from app.core.mfa import decrypt_totp_secret, verify_totp
from app.core.security import verify_password

async def verify_mfa_disable_credentials(user_type: str, user_id: UUID, password: str, code: str) -> None:
    table = "platform_users" if user_type == "platform" else "tenant_users"
    pool = get_central_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"SELECT password_hash FROM {table} WHERE id=%s AND status='active'", (str(user_id),))
            user = await cur.fetchone()
            if not user or not verify_password(password, user[0]):
                raise HTTPException(status_code=403, detail="Reauthentication failed")
            await cur.execute("SELECT secret_encrypted FROM mfa_factors WHERE user_type=%s AND user_id=%s AND factor_type='totp' AND enabled=1 LIMIT 1", (user_type, str(user_id)))
            factor = await cur.fetchone()
    if not factor or not verify_totp(decrypt_totp_secret(factor[0]), code):
        raise HTTPException(status_code=403, detail="Current MFA code is invalid")
