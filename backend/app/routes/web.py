from fastapi import APIRouter
from app.core.config import settings
from app.modules.auth.routes.v1.auth import router as auth_router
from app.modules.health.routes.v1.health import router as health_router
from app.modules.tenants.routes.v1.tenants import router as tenants_router
from app.modules.tenants.routes.v1.context import router as tenant_context_router
from app.modules.school_structure.routes.v1.structure import router as school_structure_router
from app.modules.data_transfer.routes.v1.data_transfer import router as data_transfer_router
from app.modules.students.routes.v1.students import router as students_router
from app.modules.students.routes.v1.accounts import router as student_accounts_router
from app.modules.portal.routes.v1.portal import router as portal_router
from app.modules.portal.routes.v1.student import router as student_portal_router
from app.modules.portal.routes.v1.parent import router as parent_portal_router

router = APIRouter(prefix=settings.api_v1_prefix)
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(tenants_router)
router.include_router(tenant_context_router)
router.include_router(school_structure_router)
router.include_router(data_transfer_router)
router.include_router(students_router)
router.include_router(student_accounts_router)
router.include_router(portal_router)
router.include_router(student_portal_router)
router.include_router(parent_portal_router)
