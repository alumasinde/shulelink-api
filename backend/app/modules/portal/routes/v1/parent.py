from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_principal, require_tenant_permission
from app.modules.portal.services.parent_portal import parent_portal_me

router = APIRouter(prefix="/parent-portal", tags=["Parent Portal"])


@router.get("/me")
async def me(principal=Depends(get_current_principal), tenant_id=Depends(require_tenant_permission("guardian.self"))):
    return await parent_portal_me(tenant_id, principal.user_id)
