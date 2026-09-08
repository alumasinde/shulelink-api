from fastapi import APIRouter, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.database import ping_database

router = APIRouter()
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


@router.get("/health", tags=["System"])
@limiter.limit("60/minute")
async def health(request: Request):
    return {"success": True, "data": {"service": settings.app_name, "version": settings.app_version, "status": "ok"}}


@router.get("/health/ready", tags=["System"])
@limiter.limit("30/minute")
async def readiness(request: Request):
    database_ok = await ping_database()
    status = "ready" if database_ok else "not_ready"
    return {
        "success": database_ok,
        "data": {"status": status, "checks": {"database": "ok" if database_ok else "unavailable"}},
    }
