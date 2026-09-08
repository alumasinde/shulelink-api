from fastapi import APIRouter
from app.core.config import settings
from app.modules.auth.routes.v1.auth import router as auth_router
from app.modules.health.routes.v1.health import router as health_router
from app.modules.tenants.routes.v1.tenants import router as tenants_router
from app.modules.tenants.routes.v1.context import router as tenant_context_router

router = APIRouter(prefix=settings.api_v1_prefix)
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(tenants_router)
router.include_router(tenant_context_router)
