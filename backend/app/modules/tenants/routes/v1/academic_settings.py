from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.core.dependencies import Principal, require_platform_permission
from app.modules.tenants.academic_settings import list_platform_academic_settings, update_platform_academic_setting

router = APIRouter(prefix='/platform/academic-settings', tags=['Platform Academic Settings'])


class AcademicSettingUpdate(BaseModel):
    setting_value: object | None = None
    value_type: str = Field(min_length=1, max_length=30)


@router.get('')
async def list_settings(_: Principal = Depends(require_platform_permission('academic.settings.manage'))):
    return await list_platform_academic_settings()


@router.patch('/{setting_id}')
async def update_setting(setting_id: UUID, payload: AcademicSettingUpdate, principal: Principal = Depends(require_platform_permission('academic.settings.manage'))):
    return await update_platform_academic_setting(setting_id, payload.model_dump(), principal.user_id)
