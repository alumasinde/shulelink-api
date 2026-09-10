from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from app.core.dependencies import get_current_principal, require_tenant, require_tenant_permission
from app.modules.attendance.phase_d_schemas import AttendanceCorrectionCreate, AttendanceCorrectionResponse, AttendanceExemptionCreate, AttendanceExemptionResponse
from app.modules.attendance.services.corrections import list_corrections, request_correction, resolve_correction
from app.modules.attendance.services.exemptions import cancel_exemption, create_exemption, get_exemption, list_exemptions, resolve_exemption

router = APIRouter(prefix='/attendance', tags=['Attendance Corrections & Exemptions'])
def perm(code):
    async def dependency(tenant_id: UUID = Depends(require_tenant_permission(code))): return tenant_id
    return dependency
read = perm('attendance.read'); correct = perm('attendance.correct'); approve = perm('attendance.approve')

@router.post('/corrections', response_model=AttendanceCorrectionResponse, status_code=status.HTTP_201_CREATED)
async def create_correction(payload: AttendanceCorrectionCreate, principal=Depends(get_current_principal), tenant_id: UUID = Depends(correct)):
    return await request_correction(tenant_id, principal.user_id, payload.attendance_record_id, payload.new_status_code, payload.reason)

@router.get('/corrections', response_model=list[AttendanceCorrectionResponse])
async def corrections(status_filter: str | None = Query(None, alias='status'), limit: int = Query(100, ge=1, le=200), tenant_id: UUID = Depends(read)):
    return await list_corrections(tenant_id, status_filter, limit)

@router.post('/corrections/{correction_id}/approve', response_model=AttendanceCorrectionResponse)
async def approve_correction(correction_id: UUID, principal=Depends(get_current_principal), tenant_id: UUID = Depends(approve)):
    return await resolve_correction(tenant_id, principal.user_id, correction_id, True)

@router.post('/corrections/{correction_id}/reject', response_model=AttendanceCorrectionResponse)
async def reject_correction(correction_id: UUID, principal=Depends(get_current_principal), tenant_id: UUID = Depends(approve)):
    return await resolve_correction(tenant_id, principal.user_id, correction_id, False)

@router.post('/exemptions', response_model=AttendanceExemptionResponse, status_code=status.HTTP_201_CREATED)
async def create_attendance_exemption(payload: AttendanceExemptionCreate, principal=Depends(get_current_principal), tenant_id: UUID = Depends(require_tenant)):
    return await create_exemption(tenant_id, principal.user_id, payload.student_id, payload.exemption_type, payload.starts_at, payload.ends_at, payload.reason, payload.source_type, payload.source_id)

@router.get('/exemptions', response_model=list[AttendanceExemptionResponse])
async def exemptions(student_id: UUID | None = None, status_filter: str | None = Query(None, alias='status'), limit: int = Query(100, ge=1, le=200), tenant_id: UUID = Depends(read)):
    return await list_exemptions(tenant_id, student_id, status_filter, limit)

@router.get('/exemptions/{exemption_id}', response_model=AttendanceExemptionResponse)
async def exemption(exemption_id: UUID, tenant_id: UUID = Depends(read)):
    return await get_exemption(tenant_id, exemption_id)

@router.post('/exemptions/{exemption_id}/approve', response_model=AttendanceExemptionResponse)
async def approve_exemption(exemption_id: UUID, principal=Depends(get_current_principal), tenant_id: UUID = Depends(require_tenant)):
    return await resolve_exemption(tenant_id, principal.user_id, exemption_id, True)

@router.post('/exemptions/{exemption_id}/reject', response_model=AttendanceExemptionResponse)
async def reject_exemption(exemption_id: UUID, principal=Depends(get_current_principal), tenant_id: UUID = Depends(require_tenant)):
    return await resolve_exemption(tenant_id, principal.user_id, exemption_id, False)

@router.post('/exemptions/{exemption_id}/cancel', response_model=AttendanceExemptionResponse)
async def cancel_attendance_exemption(exemption_id: UUID, principal=Depends(get_current_principal), tenant_id: UUID = Depends(require_tenant)):
    return await cancel_exemption(tenant_id, principal.user_id, exemption_id)
