import time
import uuid

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.logging import logger, request_id_context


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        incoming = request.headers.get("X-Request-ID", "").strip()
        request_id = incoming[:128] if incoming else str(uuid.uuid4())
        request.state.request_id = request_id
        token = request_id_context.set(request_id)
        started = time.perf_counter()
        status_code = 500
        response: Response | None = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except StarletteHTTPException as exc:
            status_code = exc.status_code
            raise
        except RequestValidationError:
            status_code = 422
            raise
        except RateLimitExceeded:
            status_code = 429
            raise
        except Exception:
            status_code = 500
            logger.exception("request failed", extra={"event": "http_request_failed", "method": request.method, "path": request.url.path, "status_code": 500, "client_ip": request.client.host if request.client else None})
            raise
        finally:
            logger.info(
                "request completed",
                extra={
                    "event": "http_request",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                    "client_ip": request.client.host if request.client else None,
                    "user_id": getattr(request.state, "user_id", None),
                    "user_type": getattr(request.state, "user_type", None),
                    "tenant_id": getattr(request.state, "tenant_id", None),
                },
            )
            request_id_context.reset(token)
            if response is not None:
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Content-Type-Options"] = "nosniff"
                response.headers["X-Frame-Options"] = "DENY"
                response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
                if request.url.path.startswith(settings.api_v1_prefix):
                    response.headers["Cache-Control"] = "no-store"


class RequestBodyLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > settings.max_request_body_bytes:
                    request_id = getattr(request.state, "request_id", "unknown")
                    return JSONResponse(status_code=413, content={"success": False, "error": {"code": "REQUEST_TOO_LARGE", "message": "Request body too large"}, "request_id": request_id}, headers={"X-Request-ID": request_id})
            except ValueError:
                request_id = getattr(request.state, "request_id", "unknown")
                return JSONResponse(status_code=400, content={"success": False, "error": {"code": "INVALID_CONTENT_LENGTH", "message": "Invalid Content-Length header"}, "request_id": request_id}, headers={"X-Request-ID": request_id})
        return await call_next(request)
