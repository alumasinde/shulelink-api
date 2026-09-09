from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from app.core.dependencies import require_tenant_permission
from app.modules.academics.schemas import *
from app.modules.academics.service import *

router=APIRouter(prefix='/academics',tags=['Academics'])

def perm(code):
    async def dependency(tenant_id: UUID=Depends(require_tenant_permission(code))): return tenant_id
    return dependency

read=perm('academics.read'); manage=perm('academics.manage'); teacher_read=perm('teachers.read'); teacher_manage=perm('teachers.manage'); assign_read=perm('assignments.read'); assign_manage=perm('assignments.manage'); tt_read=perm('timetable.read'); tt_manage=perm('timetable.manage'); tt_generate=perm('timetable.generate')

@router.get('/teachers',response_model=list[TeacherResponse])
async def teachers(tenant_id=Depends(teacher_read), status: str|None=Query(None,pattern='^(active|inactive|on_leave|terminated)$'), search: str|None=Query(None,max_length=100)): return await list_teachers(tenant_id,status,search)

@router.get('/teachers/{teacher_id}',response_model=TeacherResponse)
async def teacher(teacher_id:UUID,tenant_id=Depends(teacher_read)): return await get_teacher(tenant_id,teacher_id)

@router.post('/teachers',response_model=TeacherResponse,status_code=status.HTTP_201_CREATED)
async def create_teacher_route(payload:TeacherCreate,tenant_id=Depends(teacher_manage)): return await create_teacher(tenant_id,payload.model_dump())

@router.patch('/teachers/{teacher_id}',response_model=TeacherResponse)
async def update_teacher_route(teacher_id:UUID,payload:TeacherUpdate,tenant_id=Depends(teacher_manage)): return await update_teacher(tenant_id,teacher_id,payload.model_dump(exclude_unset=True))

@router.get('/assignments',response_model=list[AssignmentResponse])
async def assignments(tenant_id=Depends(assign_read),academic_year_id:UUID|None=None,academic_term_id:UUID|None=None,teacher_id:UUID|None=None,class_level_id:UUID|None=None): return await list_assignments(tenant_id,academic_year_id,academic_term_id,teacher_id,class_level_id)

@router.post('/assignments',response_model=AssignmentResponse,status_code=status.HTTP_201_CREATED)
async def create_assignment_route(payload:AssignmentCreate,tenant_id=Depends(assign_manage)): return await create_assignment(tenant_id,payload.model_dump())

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
