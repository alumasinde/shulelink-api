from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import require_tenant_permission
from app.modules.attendance.phase2_schemas import AttendanceDashboard, AttendanceSessionCompletion, AttendanceSessionListItem
from app.modules.attendance.services.operations import dashboard, list_sessions, operational_roster, session_completion

router = APIRouter(prefix='/attendance', tags=['Attendance Operations'])

def perm(code):
    async def dependency(tenant_id: UUID = Depends(require_tenant_permission(code))): return tenant_id
    return dependency
read=perm('attendance.read')

@router.get('/dashboard', response_model=AttendanceDashboard)
async def attendance_dashboard(attendance_date: date | None = Query(None), tenant_id: UUID = Depends(read)):
    return await dashboard(tenant_id, attendance_date or date.today())

@router.get('/sessions', response_model=list[AttendanceSessionListItem])
async def attendance_sessions(attendance_date: date | None = Query(None), session_type: str | None = Query(None, min_length=1, max_length=64), session_status: str | None = Query(None, alias='status', min_length=1, max_length=32), class_level_id: UUID | None = Query(None), stream_id: UUID | None = Query(None), limit: int = Query(100, ge=1, le=200), tenant_id: UUID = Depends(read)):
    return await list_sessions(tenant_id, attendance_date, session_type, session_status, class_level_id, stream_id, limit)

@router.get('/sessions/{session_id}/completion', response_model=AttendanceSessionCompletion)
async def completion(session_id: UUID, tenant_id: UUID = Depends(read)):
    return await session_completion(tenant_id, session_id)

@router.get('/sessions/{session_id}/operational-roster')
async def operational_session_roster(session_id: UUID, residency_type: str | None = Query(None, pattern='^(day_scholar|boarder)$'), status_code: str | None = Query(None, min_length=1, max_length=64), tenant_id: UUID = Depends(read)):
    return await operational_roster(tenant_id, session_id, residency_type, status_code)
