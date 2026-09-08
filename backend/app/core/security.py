from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from uuid import uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


def validate_password(password: str) -> None:
    if len(password) < settings.password_min_length:
        raise ValueError(f"Password must be at least {settings.password_min_length} characters")
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain an uppercase letter")
    if not any(c.islower() for c in password):
        raise ValueError("Password must contain a lowercase letter")
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain a number")


def create_access_token(*, user_id: str, user_type: str, tenant_id: str | None, session_id: str, access_session_id: str | None = None) -> tuple[str, datetime]:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.access_token_minutes)
    payload = {"sub": user_id, "typ": user_type, "tid": tenant_id, "sid": session_id, "jti": str(uuid4()), "iat": now, "exp": expires}
    if access_session_id:
        payload["tas"] = access_session_id
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm), expires


def create_refresh_token() -> tuple[str, str, datetime]:
    raw = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days)
    return raw, token_hash, expires


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
