import secrets

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.cookies import CSRF_COOKIE

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
_EXEMPT_PATHS = {f"{settings.api_v1_prefix}/auth/csrf"}


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.auth_cookie_mode or request.method in _SAFE_METHODS or request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        cookie_token = request.cookies.get(CSRF_COOKIE)
        header_token = request.headers.get("X-CSRF-Token")
        if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
            request_id = getattr(request.state, "request_id", "unknown")
            return JSONResponse(
                status_code=403,
                content={
                    "success": False,
                    "error": {"code": "CSRF_VALIDATION_FAILED", "message": "CSRF validation failed"},
                    "request_id": request_id,
                },
                headers={"X-Request-ID": request_id},
            )
        return await call_next(request)
