from fastapi import APIRouter, Depends
from app.core.dependencies import Principal, get_current_principal, require_tenant_permission
from app.modules.auth.access import get_role_context
from app.modules.portal.services.student_portal import student_portal_me
from app.modules.portal.services.parent_portal import parent_portal_me

router = APIRouter(prefix="/portal", tags=["Portal"])


@router.get("/me")
async def portal_me(
    principal: Principal = Depends(get_current_principal),
    tenant_id=Depends(require_tenant_permission("portal.dashboard")),
):
    context = await get_role_context(principal.user_id, principal.user_type, tenant_id)
    if context.get("portal") == "student":
        return await student_portal_me(tenant_id, principal.user_id)
    if context.get("portal") == "parent":
        return await parent_portal_me(tenant_id, principal.user_id)
    return {"portal": context.get("portal", "school"), "profile": {"user_id": str(principal.user_id)}}
