from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, Header, status
from app.core.dependencies import get_current_principal, require_tenant_permission
from app.core.database import get_pool
from app.modules.attendance.engine import close, create_session, get_session, mark, roster
from app.modules.attendance.schemas import AttendanceMarkRequest, AttendanceMarkResult, AttendanceSessionCloseResponse, AttendanceSessionCreate, AttendanceSessionResponse, AttendanceStatusResponse, RosterStudent
from app.modules.attendance.services.capture_rules import apply_approved_exemptions
from app.modules.attendance.services.nemis import stage_daily_attendance
from app.modules.attendance.services.sync import receive_batch
router = APIRouter(prefix='/attendance', tags=['Attendance'])
def perm(code):
    async def dependency(tenant_id: UUID = Depends(require_tenant_permission(code))): return tenant_id
    return dependency
read=perm('attendance.read'); manage=perm('attendance.manage'); mark_perm=perm('attendance.mark'); sync_perm=perm('attendance.sync'); nemis_perm=perm('attendance.nemis')
@router.get('/statuses', response_model=list[AttendanceStatusResponse])
async def statuses(tenant_id: UUID = Depends(read)):
    pool=get_pool()
    async with pool.acquire() as c:
        async with c.cursor() as cur:
            await cur.execute('SELECT id,code,name,description,category,is_system,is_active,sort_order FROM attendance_statuses WHERE tenant_id=%s ORDER BY sort_order,code',(str(tenant_id),)); rows=await cur.fetchall()
    return [dict(zip(['id','code','name','description','category','is_system','is_active','sort_order'],r)) for r in rows]
@router.get('/sessions/{session_id}', response_model=AttendanceSessionResponse)
async def session(session_id: UUID, tenant_id: UUID = Depends(read)): return await get_session(tenant_id,session_id)
@router.get('/sessions/{session_id}/roster', response_model=list[RosterStudent])
async def session_roster(session_id: UUID, tenant_id: UUID = Depends(read)): return await roster(tenant_id,session_id)
@router.post('/sessions', response_model=AttendanceSessionResponse, status_code=status.HTTP_201_CREATED)
async def open_session(payload: AttendanceSessionCreate, principal=Depends(get_current_principal), tenant_id: UUID = Depends(manage)):
    session_id=await create_session(tenant_id,principal.user_id,payload.model_dump()); return await get_session(tenant_id,session_id)
@router.post('/sessions/{session_id}/records', response_model=AttendanceMarkResult)
async def record(session_id: UUID, payload: AttendanceMarkRequest, principal=Depends(get_current_principal), tenant_id: UUID = Depends(mark_perm), x_idempotency_key: str | None = Header(None, alias='X-Idempotency-Key')):
    payload=await apply_approved_exemptions(tenant_id,session_id,payload)
    return await mark(tenant_id,principal.user_id,session_id,payload,x_idempotency_key)
@router.post('/sessions/{session_id}/close', response_model=AttendanceSessionCloseResponse)
async def close_session(session_id: UUID, principal=Depends(get_current_principal), tenant_id: UUID = Depends(manage)): return await close(tenant_id,principal.user_id,session_id)
@router.post('/sync/batches')
async def sync_batch(payload: dict, principal=Depends(get_current_principal), tenant_id: UUID = Depends(sync_perm)):
    return await receive_batch(tenant_id,str(payload.get('client_batch_id','')),payload.get('items') or [],UUID(str(payload['device_id'])) if payload.get('device_id') else None)
@router.post('/nemis/stage')
async def stage_nemis(attendance_date: date, academic_year_id: UUID | None = None, academic_term_id: UUID | None = None, tenant_id: UUID = Depends(nemis_perm)): return await stage_daily_attendance(tenant_id,attendance_date,academic_year_id,academic_term_id)
