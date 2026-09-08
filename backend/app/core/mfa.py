import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

from app.core.crypto import decrypt_secret, encrypt_secret


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _normalized_secret(secret: str) -> bytes:
    padded = secret.strip().upper() + "=" * (-len(secret.strip()) % 8)
    return base64.b32decode(padded, casefold=True)


def totp_code(secret: str, timestamp: int | None = None) -> str:
    counter = int((timestamp if timestamp is not None else time.time()) // 30)
    digest = hmac.new(_normalized_secret(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return f"{number % 1_000_000:06d}"


def verify_totp(secret: str, code: str, window: int = 1) -> bool:
    code = code.strip()
    if len(code) != 6 or not code.isdigit():
        return False
    now = int(time.time())
    return any(hmac.compare_digest(totp_code(secret, now + step * 30), code) for step in range(-window, window + 1))


def otpauth_uri(secret: str, issuer: str, account: str) -> str:
    label = f"{quote(issuer)}:{quote(account)}"
    return f"otpauth://totp/{label}?secret={quote(secret)}&issuer={quote(issuer)}&algorithm=SHA1&digits=6&period=30"


def encrypt_totp_secret(secret: str) -> str:
    return encrypt_secret(secret)


def decrypt_totp_secret(value: str) -> str:
    return decrypt_secret(value)


def generate_recovery_codes(count: int = 10) -> list[str]:
    return [f"{secrets.token_hex(5)}" for _ in range(count)]


def hash_recovery_code(code: str) -> str:
    return hashlib.sha256(code.strip().lower().encode()).hexdigest()
