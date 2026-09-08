from uuid import UUID
from fastapi import HTTPException
from app.modules.portal.repositories.student_portal import get_student_portal


async def student_portal_me(tenant_id: UUID, tenant_user_id: UUID):
    profile = await get_student_portal(tenant_id, tenant_user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile is not linked to this portal account")
    return {"portal": "student", "profile": profile}
