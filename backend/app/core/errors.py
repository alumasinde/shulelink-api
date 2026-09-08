from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import logger


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _response(request: Request, status_code: int, code: str, message: str, details=None, headers=None):
    error = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    response = JSONResponse(
        status_code=status_code,
        content={"success": False, "error": error, "request_id": _request_id(request)},
        headers=headers,
    )
    response.headers["X-Request-ID"] = _request_id(request)
    return response


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_exception(request: Request, exc: RateLimitExceeded):
        logger.warning(
            "rate limit exceeded",
            extra={
                "event": "rate_limit_exceeded",
                "method": request.method,
                "path": request.url.path,
                "status_code": 429,
                "client_ip": request.client.host if request.client else None,
            },
        )
        return _response(request, 429, "RATE_LIMIT_EXCEEDED", "Too many requests. Please try again later.", headers={"Retry-After": "60"})

    @app.exception_handler(StarletteHTTPException)
    async def http_exception(request: Request, exc: StarletteHTTPException):
        if exc.status_code >= 500:
            logger.error("http server error", extra={"event": "http_error", "method": request.method, "path": request.url.path, "status_code": exc.status_code})
        elif exc.status_code in {401, 403, 404, 409, 422}:
            logger.warning("http client/security error", extra={"event": "http_error", "method": request.method, "path": request.url.path, "status_code": exc.status_code})
        message = str(exc.detail) if exc.status_code < 500 else "An unexpected error occurred"
        return _response(request, exc.status_code, "HTTP_ERROR", message)

    @app.exception_handler(RequestValidationError)
    async def validation_exception(request: Request, exc: RequestValidationError):
        logger.warning(
            "request validation failed",
            extra={"event": "validation_error", "method": request.method, "path": request.url.path, "status_code": 422},
        )
        return _response(request, 422, "VALIDATION_ERROR", "Request validation failed", exc.errors())

    @app.exception_handler(Exception)
    async def unhandled_exception(request: Request, exc: Exception):
        logger.exception(
            "unhandled application exception",
            extra={"event": "unhandled_exception", "method": request.method, "path": request.url.path, "status_code": 500},
        )
        return _response(request, 500, "INTERNAL_ERROR", "An unexpected error occurred")
