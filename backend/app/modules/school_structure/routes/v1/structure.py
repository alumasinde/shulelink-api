from uuid import UUID
from fastapi import APIRouter, Depends
from app.core.dependencies import Principal, get_current_principal, require_tenant_permission
from app.modules.school_structure.schemas import *
from app.modules.school_structure.service import *

router=APIRouter(prefix='/school-structure',tags=['School Structure'])
async def read_tenant(tenant_id: UUID=Depends(require_tenant_permission('school.structure.read'))): return tenant_id
async def manage_tenant(tenant_id: UUID=Depends(require_tenant_permission('school.structure.manage'))): return tenant_id

@router.get('/campuses',response_model=list[CampusResponse])
async def campuses(tenant_id=Depends(read_tenant)): return await list_items('campuses',tenant_id)
@router.post('/campuses',response_model=CampusResponse,status_code=201)
async def create_campus(payload:CampusCreate,tenant_id=Depends(manage_tenant)): return await create_item('campuses',tenant_id,payload.model_dump())
@router.get('/academic-years',response_model=list[AcademicYearResponse])
async def academic_years(tenant_id=Depends(read_tenant)): return await list_items('academic_years',tenant_id)
@router.post('/academic-years',response_model=AcademicYearResponse,status_code=201)
async def create_year(payload:AcademicYearCreate,tenant_id=Depends(manage_tenant)): return await create_item('academic_years',tenant_id,payload.model_dump())
@router.get('/terms',response_model=list[TermResponse])
async def terms(tenant_id=Depends(read_tenant)): return await list_items('academic_terms',tenant_id)
@router.post('/terms',response_model=TermResponse,status_code=201)
async def create_term(payload:TermCreate,tenant_id=Depends(manage_tenant)): return await create_item('academic_terms',tenant_id,payload.model_dump())
@router.get('/departments',response_model=list[DepartmentResponse])
async def departments(tenant_id=Depends(read_tenant)): return await list_items('departments',tenant_id)
@router.post('/departments',response_model=DepartmentResponse,status_code=201)
async def create_department(payload:DepartmentCreate,tenant_id=Depends(manage_tenant)): return await create_item('departments',tenant_id,payload.model_dump())
@router.get('/classes',response_model=list[ClassLevelResponse])
async def classes(tenant_id=Depends(read_tenant)): return await list_items('class_levels',tenant_id)
@router.post('/classes',response_model=ClassLevelResponse,status_code=201)
async def create_class(payload:ClassLevelCreate,tenant_id=Depends(manage_tenant)): return await create_item('class_levels',tenant_id,payload.model_dump())
@router.get('/streams',response_model=list[StreamResponse])
async def streams(tenant_id=Depends(read_tenant)): return await list_items('streams',tenant_id)
@router.post('/streams',response_model=StreamResponse,status_code=201)
async def create_stream(payload:StreamCreate,tenant_id=Depends(manage_tenant)): return await create_item('streams',tenant_id,payload.model_dump())
@router.get('/subjects',response_model=list[SubjectResponse])
async def subjects(tenant_id=Depends(read_tenant)): return await list_items('subjects',tenant_id)
@router.post('/subjects',response_model=SubjectResponse,status_code=201)
async def create_subject(payload:SubjectCreate,tenant_id=Depends(manage_tenant)): return await create_item('subjects',tenant_id,payload.model_dump())
@router.get('/class-subjects')
async def class_subjects(tenant_id=Depends(read_tenant)): return await list_assignments(tenant_id)
@router.post('/class-subjects',response_model=ClassSubjectResponse,status_code=201)
async def add_class_subject(payload:ClassSubjectCreate,tenant_id=Depends(manage_tenant)): return await assign_subject(tenant_id,payload.model_dump())
@router.get('/settings',response_model=list[SettingResponse])
async def settings(tenant_id=Depends(read_tenant)): return await list_settings(tenant_id)
@router.put('/settings/{setting_key}',response_model=SettingResponse)
async def update_setting(setting_key:str,payload:SettingUpdate,tenant_id=Depends(manage_tenant),principal:Principal=Depends(get_current_principal)):
    return await upsert_setting(tenant_id,setting_key,payload.model_dump(),principal.user_id)
