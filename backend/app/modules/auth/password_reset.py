from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
import secrets
from app.core.config import settings
from app.core.database import get_central_pool
from app.core.security import hash_token
from app.modules.auth.email import send_password_reset_email

async def request_password_reset_scoped(user_type: str, email: str, tenant_id: UUID | None = None) -> str | None:
    normalized=email.strip().lower(); token=None
    pool=get_central_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            if user_type=="tenant":
                if tenant_id is None:return None
                await cur.execute("SELECT u.id,u.status FROM tenant_users u JOIN tenant_memberships m ON m.tenant_user_id=u.id WHERE m.tenant_id=%s AND m.status='active' AND u.email=%s LIMIT 1",(str(tenant_id),normalized))
            else:
                await cur.execute("SELECT id,status FROM platform_users WHERE email=%s LIMIT 1",(normalized,))
            row=await cur.fetchone()
            if row and row[1]=="active":
                token=secrets.token_urlsafe(48); expires=datetime.now(timezone.utc).replace(tzinfo=None)+timedelta(minutes=settings.password_reset_minutes)
                await cur.execute("UPDATE password_reset_tokens SET used_at=NOW() WHERE user_type=%s AND user_id=%s AND used_at IS NULL",(user_type,str(row[0])))
                await cur.execute("INSERT INTO password_reset_tokens (id,user_type,user_id,token_hash,expires_at) VALUES (%s,%s,%s,%s,%s)",(str(uuid4()),user_type,str(row[0]),hash_token(token),expires))
    if not token:return None
    if settings.auth_reset_return_token:return token
    try: await send_password_reset_email(normalized,token)
    except Exception:return None
    return None
