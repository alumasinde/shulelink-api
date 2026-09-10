from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.core.database import close_database, initialize_database
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestBodyLimitMiddleware, RequestContextMiddleware
from app.core.csrf import CSRFMiddleware
from app.core.rate_limit import limiter
from app.core.tenant_db import close_tenant_pools
from app.routes.web import router

logger = logging.getLogger("shulelink")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Database schema migrations are intentionally not run by the API process.
    # The deployment orchestrator runs the one-shot migration job first and only
    # starts the API after that job completes successfully.
    await initialize_database()
    logger.info("database pool initialized", extra={"event": "database_pool_ready"})
    try:
        yield
    finally:
        await close_tenant_pools()
        await close_database()
        logger.info("application resources closed", extra={"event": "application_shutdown"})


def create_app() -> FastAPI:
    configure_logging()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )
    application.state.limiter = limiter
    register_exception_handlers(application)
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(RequestBodyLimitMiddleware)
    application.add_middleware(CSRFMiddleware)
    application.add_middleware(SlowAPIMiddleware)
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_host_list)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID", "X-CSRF-Token"],
    )
    application.include_router(router)

    @application.get("/", include_in_schema=False)
    async def root():
        return {"name": settings.app_name, "version": settings.app_version, "status": "ok"}

    return application


app = create_app()
