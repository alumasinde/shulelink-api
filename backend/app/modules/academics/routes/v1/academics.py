from uuid import UUID
from fastapi import APIRouter, Depends, Query, status, HTTPException
from app.core.dependencies import require_tenant_permission
from app.modules.academics.schemas import *
from app.modules.academics.service import *
from app.modules.academics.bulk import bulk_update_teachers, bulk_replace_teacher_subjects
from app.modules.academics.teacher_subjects import list_teacher_subjects, replace_teacher_subjects, list_department_subjects
from app.modules.academics.configuration import effective_academic_configuration

router=APIRouter(prefix='/academics',tags=['Academics'])

def perm(code):
    async def dependency(tenant_id: UUID=Depends(require_tenant_permission(code))): return tenant_id
    return dependency

read=perm('academics.read'); manage=perm('academics.manage'); teacher_read=perm('teachers.read'); teacher_manage=perm('teachers.manage'); assign_read=perm('assignments.read'); assign_manage=perm('assignments.manage'); tt_read=perm('timetable.read'); tt_manage=perm('timetable.manage'); tt_generate=perm('timetable.generate')


@router.get('/configuration', response_model=EffectiveAcademicSettingsResponse)
async def configuration(tenant_id=Depends(read)):
    return await effective_academic_configuration(tenant_id)


@router.get('/teachers',response_model=list[TeacherResponse])
async def teachers(tenant_id=Depends(teacher_read), status: str|None=Query(None,max_length=40), search: str|None=Query(None,max_length=100)):
    return await list_teachers(tenant_id,status,search)

@router.get('/teachers/{teacher_id}',response_model=TeacherResponse)
async def teacher(teacher_id:UUID,tenant_id=Depends(teacher_read)):
    item=await get_teacher(tenant_id,teacher_id); item['subjects']=await list_teacher_subjects(tenant_id,teacher_id); item['subject_ids']=[x['id'] for x in item['subjects']]; return item

@router.get('/teachers/{teacher_id}/subjects')
async def teacher_subjects(teacher_id:UUID,tenant_id=Depends(teacher_read)): return await list_teacher_subjects(tenant_id,teacher_id)

@router.get('/departments/{department_id}/subjects')
async def department_subjects(department_id:UUID,tenant_id=Depends(teacher_read)): return await list_department_subjects(tenant_id,department_id)

@router.put('/teachers/{teacher_id}/subjects')
async def update_teacher_subjects(teacher_id:UUID,payload:dict,tenant_id=Depends(teacher_manage)):
    subject_ids=payload.get('subject_ids',[])
    if not isinstance(subject_ids,list): raise HTTPException(422,'subject_ids must be an array')
    try: ids=[UUID(x) for x in subject_ids]
    except (ValueError,TypeError): raise HTTPException(422,'subject_ids must contain valid UUIDs')
    return await replace_teacher_subjects(tenant_id,teacher_id,ids)

@router.post('/teachers/bulk-update')
async def bulk_update_teachers_route(payload:BulkTeacherUpdate,tenant_id=Depends(teacher_manage)):
    return await bulk_update_teachers(tenant_id,payload.teacher_ids,payload.model_dump(exclude={'teacher_ids'}, exclude_none=True))

@router.put('/teachers/bulk-subjects')
async def bulk_teacher_subjects_route(payload:BulkTeacherSubjects,tenant_id=Depends(teacher_manage)):
    return await bulk_replace_teacher_subjects(tenant_id,payload.teacher_ids,payload.subject_ids)

@router.post('/teachers',response_model=TeacherResponse,status_code=status.HTTP_201_CREATED)
async def create_teacher_route(payload:TeacherCreate,tenant_id=Depends(teacher_manage)):
    p=payload.model_dump(); subject_ids=p.pop('subject_ids',[]); teacher=await create_teacher(tenant_id,p)
    if subject_ids: await replace_teacher_subjects(tenant_id,teacher['id'],subject_ids)
    return await teacher(teacher['id'],tenant_id)

@router.patch('/teachers/{teacher_id}',response_model=TeacherResponse)
async def update_teacher_route(teacher_id:UUID,payload:TeacherUpdate,tenant_id=Depends(teacher_manage)):
    p=payload.model_dump(exclude_unset=True); subject_ids=p.pop('subject_ids',None); await update_teacher(tenant_id,teacher_id,p)
    if subject_ids is not None: await replace_teacher_subjects(tenant_id,teacher_id,subject_ids)
    return await teacher(teacher_id,tenant_id)

@router.get('/assignments',response_model=list[AssignmentResponse])
async def assignments(tenant_id=Depends(assign_read),academic_year_id:UUID|None=None,academic_term_id:UUID|None=None,teacher_id:UUID|None=None,class_level_id:UUID|None=None): return await list_assignments(tenant_id,academic_year_id,academic_term_id,teacher_id,class_level_id)
@router.post('/assignments',response_model=AssignmentResponse,status_code=status.HTTP_201_CREATED)
async def create_assignment_route(payload:AssignmentCreate,tenant_id=Depends(assign_manage)):
    allowed={x['id'] for x in await list_teacher_subjects(tenant_id,payload.teacher_id)}
    if str(payload.subject_id) not in allowed: raise HTTPException(400,'Teacher is not configured to teach this subject. Configure teacher subject eligibility first.')
    return await create_assignment(tenant_id,payload.model_dump())
@router.delete('/assignments/{assignment_id}',status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment_route(assignment_id:UUID,tenant_id=Depends(assign_manage)): await delete_assignment(tenant_id,assignment_id)

@router.get('/timetable/rooms',response_model=list[RoomResponse])
async def rooms(tenant_id=Depends(tt_read)): return await list_rooms(tenant_id)
@router.post('/timetable/rooms',response_model=RoomResponse,status_code=status.HTTP_201_CREATED)
async def create_room_route(payload:RoomCreate,tenant_id=Depends(tt_manage)): return await create_room(tenant_id,payload.model_dump())
@router.put('/timetable/rooms/{room_id}',response_model=RoomResponse)
async def update_room_route(room_id:UUID,payload:RoomUpdate,tenant_id=Depends(tt_manage)): return await update_room(tenant_id,room_id,payload.model_dump())
@router.get('/timetable/periods',response_model=list[PeriodResponse])
async def periods(tenant_id=Depends(tt_read)): return await list_periods(tenant_id)
@router.post('/timetable/periods',response_model=PeriodResponse,status_code=status.HTTP_201_CREATED)
async def create_period_route(payload:PeriodCreate,tenant_id=Depends(tt_manage)): return await create_period(tenant_id,payload.model_dump())
@router.put('/timetable/periods/{period_id}',response_model=PeriodResponse)
async def update_period_route(period_id:UUID,payload:PeriodUpdate,tenant_id=Depends(tt_manage)): return await update_period(tenant_id,period_id,payload.model_dump())
@router.get('/timetable',response_model=list[TimetableResponse])
async def timetable(tenant_id=Depends(tt_read),academic_term_id:UUID|None=None,class_level_id:UUID|None=None,stream_id:UUID|None=None,day_of_week:int|None=Query(None,ge=1,le=7)): return await list_timetable(tenant_id,academic_term_id,class_level_id,stream_id,day_of_week)
@router.post('/timetable',response_model=TimetableResponse,status_code=status.HTTP_201_CREATED)
async def create_timetable_route(payload:TimetableCreate,tenant_id=Depends(tt_manage)): return await create_timetable(tenant_id,payload.model_dump())
@router.delete('/timetable/{entry_id}',status_code=status.HTTP_204_NO_CONTENT)
async def delete_timetable_route(entry_id:UUID,tenant_id=Depends(tt_manage)): await delete_timetable(tenant_id,entry_id)
@router.post('/timetable/generate',response_model=GenerateResponse)
async def generate(payload:GenerateRequest,tenant_id=Depends(tt_generate)): return await generate_timetable(tenant_id,payload.model_dump())
