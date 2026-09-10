from uuid import UUID
from fastapi import APIRouter, Depends, Header, status
from app.core.dependencies import get_current_principal, require_tenant_permission
from app.modules.attendance.schemas import AttendanceMarkRequest, AttendanceMarkResult, AttendanceSessionCloseResponse, AttendanceSessionCreate, AttendanceSessionResponse, AttendanceStatusResponse, RosterStudent
from app.modules.attendance.engine import close, create_session, get_session, mark, roster

router=APIRouter(prefix='/attendance',tags=['Attendance'])
def perm(code):
    async def dependency(tenant_id: UUID=Depends(require_tenant_permission(code))): return tenant_id
    return dependency
read=perm('attendance.read'); manage=perm('attendance.manage'); mark_perm=perm('attendance.mark')
@router.get('/sessions/{session_id}',response_model=AttendanceSessionResponse)
async def session(session_id:UUID,tenant_id:UUID=Depends(read)): return await get_session(tenant_id,session_id)
@router.get('/sessions/{session_id}/roster',response_model=list[RosterStudent])
async def session_roster(session_id:UUID,tenant_id:UUID=Depends(read)): return await roster(tenant_id,session_id)
@router.post('/sessions',response_model=AttendanceSessionResponse,status_code=status.HTTP_201_CREATED)
async def open_session(payload:AttendanceSessionCreate,principal=Depends(get_current_principal),tenant_id:UUID=Depends(manage)):
    i=await create_session(tenant_id,principal.user_id,payload.model_dump()); return await get_session(tenant_id,i)
@router.post('/sessions/{session_id}/records',response_model=AttendanceMarkResult)
async def record(session_id:UUID,payload:AttendanceMarkRequest,principal=Depends(get_current_principal),tenant_id:UUID=Depends(mark_perm),x_idempotency_key:str|None=Header(None,alias='X-Idempotency-Key')):
    return await mark(tenant_id,principal.user_id,session_id,payload,x_idempotency_key)
@router.post('/sessions/{session_id}/close',response_model=AttendanceSessionCloseResponse)
async def close_session(session_id:UUID,principal=Depends(get_current_principal),tenant_id:UUID=Depends(manage)):
    return await close(tenant_id,principal.user_id,session_id)
