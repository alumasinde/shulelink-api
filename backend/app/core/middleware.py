import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

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
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            logger.exception(
                "request failed",
                extra={
                    "event": "http_request_failed",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "client_ip": request.client.host if request.client else None,
                },
            )
            raise
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info(
                "request completed",
                extra={
                    "event": "http_request",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "client_ip": request.client.host if request.client else None,
                },
            )
            request_id_context.reset(token)
            if "response" in locals():
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Content-Type-Options"] = "nosniff"
                response.headers["X-Frame-Options"] = "DENY"
                response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
                response.headers["Cache-Control"] = "no-store" if request.url.path.startswith(settings.api_v1_prefix) else response.headers.get("Cache-Control", "")


class RequestBodyLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > settings.max_request_body_bytes:
                    return Response("Request body too large", status_code=413, headers={"X-Request-ID": getattr(request.state, "request_id", "")})
            except ValueError:
                return Response("Invalid Content-Length", status_code=400)
        return await call_next(request)
