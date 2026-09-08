from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_principal, require_tenant_permission
from app.modules.portal.services.student_portal import student_portal_me

router = APIRouter(prefix="/student-portal", tags=["Student Portal"])


@router.get("/me")
async def me(principal=Depends(get_current_principal), tenant_id=Depends(require_tenant_permission("students.self"))):
    return await student_portal_me(tenant_id, principal.user_id)
