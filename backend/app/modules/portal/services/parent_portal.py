from uuid import UUID
from fastapi import HTTPException
from app.modules.portal.repositories.parent_portal import get_parent_portal


async def parent_portal_me(tenant_id: UUID, tenant_user_id: UUID):
    profile = await get_parent_portal(tenant_id, tenant_user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Parent profile is not linked to this portal account")
    return {"portal": "parent", "profile": {k: v for k, v in profile.items() if k != "children"}, "children": profile["children"]}
