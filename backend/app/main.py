from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.core.database import close_database, initialize_database
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestBodyLimitMiddleware, RequestContextMiddleware
from app.modules.health.routes.v1.health import limiter
from app.routes.web import router

logger = logging.getLogger("shulelink")


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        await initialize_database()
        logger.info("database pool initialized")
    except Exception:
        logger.exception("database initialization failed; readiness will remain unavailable")
    yield
    await close_database()


def create_app() -> FastAPI:
    configure_logging()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    register_exception_handlers(application)
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(RequestBodyLimitMiddleware)
    application.add_middleware(SlowAPIMiddleware)
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_host_list)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
    )
    application.include_router(router)

    @application.get("/", include_in_schema=False)
    async def root():
        return {"name": settings.app_name, "version": settings.app_version, "status": "ok"}

    return application


app = create_app()
