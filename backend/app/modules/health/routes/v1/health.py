from fastapi import APIRouter, Request

from app.core.config import settings
from app.core.database import ping_database
from app.core.rate_limit import limiter

router = APIRouter()


@router.get("/health", tags=["System"])
@limiter.limit("60/minute")
async def health(request: Request):
    return {"success": True, "data": {"service": settings.app_name, "version": settings.app_version, "status": "ok"}}


@router.get("/health/ready", tags=["System"])
@limiter.limit("30/minute")
async def readiness(request: Request):
    database_ok = await ping_database()
    return {"success": database_ok, "data": {"status": "ready" if database_ok else "not_ready", "checks": {"database": "ok" if database_ok else "unavailable"}}}
