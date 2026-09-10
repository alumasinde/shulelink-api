from uuid import UUID
from fastapi import APIRouter, Depends
from app.core.dependencies import Principal, get_current_principal, require_platform_permission, require_tenant_permission
from app.modules.curriculum.schemas import CurriculumTemplateCreate, CurriculumTemplateUpdate, CurriculumTemplateCloneRequest, CurriculumSelectRequest
from app.modules.curriculum.service import list_templates, get_template, create_template, update_template, clone_template, publish_template, archive_template, published_template_summaries, school_curriculum_configuration, select_school_template

platform_router = APIRouter(prefix='/platform/curriculum', tags=['Platform Curriculum'])
tenant_router = APIRouter(prefix='/curriculum', tags=['School Curriculum'])

@platform_router.get('/templates')
async def platform_list(_: Principal = Depends(require_platform_permission('curriculum.manage'))): return await list_templates(False)

@platform_router.get('/templates/{template_id}')
async def platform_get(template_id: UUID, _: Principal = Depends(require_platform_permission('curriculum.manage'))): return await get_template(template_id)

@platform_router.post('/templates', status_code=201)
async def platform_create(payload: CurriculumTemplateCreate, principal: Principal = Depends(require_platform_permission('curriculum.manage'))): return await create_template(payload, principal.user_id)

@platform_router.put('/templates/{template_id}')
async def platform_update(template_id: UUID, payload: CurriculumTemplateUpdate, principal: Principal = Depends(require_platform_permission('curriculum.manage'))): return await update_template(template_id, payload, principal.user_id)

@platform_router.post('/templates/{template_id}/clone', status_code=201)
async def platform_clone(template_id: UUID, payload: CurriculumTemplateCloneRequest, principal: Principal = Depends(require_platform_permission('curriculum.manage'))): return await clone_template(template_id, payload, principal.user_id)

@platform_router.post('/templates/{template_id}/publish')
async def platform_publish(template_id: UUID, principal: Principal = Depends(require_platform_permission('curriculum.manage'))): return await publish_template(template_id, principal.user_id)

@platform_router.post('/templates/{template_id}/archive')
async def platform_archive(template_id: UUID, principal: Principal = Depends(require_platform_permission('curriculum.manage'))): return await archive_template(template_id, principal.user_id)

@tenant_router.get('/templates')
async def school_templates(_: UUID = Depends(require_tenant_permission('curriculum.read'))): return await published_template_summaries()

@tenant_router.get('/configuration')
async def school_configuration(_: UUID = Depends(require_tenant_permission('curriculum.read'))): return await school_curriculum_configuration()

@tenant_router.post('/select-template')
async def school_select_template(payload: CurriculumSelectRequest, tenant_id: UUID = Depends(require_tenant_permission('curriculum.manage')), principal: Principal = Depends(get_current_principal)):
    return await select_school_template(payload, tenant_id, principal.user_id)
