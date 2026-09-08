from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr

from app.core.dependencies import require_tenant_permission
from app.modules.students.account_service import (
    get_guardian_account_status,
    get_student_account_status,
    provision_guardian_account,
    provision_student_account,
    resend_guardian_activation,
    resend_student_activation,
)

router = APIRouter(prefix="/student-accounts", tags=["Portal Accounts"])


class GuardianAccountRequest(BaseModel):
    email: EmailStr


class StudentAccountRequest(BaseModel):
    email: EmailStr | None = None


@router.get("/guardians/{guardian_id}")
async def guardian_account_status(
    guardian_id: UUID,
    tenant_id=Depends(require_tenant_permission("accounts.manage")),
):
    return await get_guardian_account_status(tenant_id, guardian_id)


@router.post("/guardians/{guardian_id}")
async def guardian_account(
    guardian_id: UUID,
    payload: GuardianAccountRequest,
    tenant_id=Depends(require_tenant_permission("accounts.manage")),
):
    return await provision_guardian_account(tenant_id, guardian_id, payload.email)


@router.post("/guardians/{guardian_id}/resend-activation")
async def guardian_resend_activation(
    guardian_id: UUID,
    tenant_id=Depends(require_tenant_permission("accounts.manage")),
):
    return await resend_guardian_activation(tenant_id, guardian_id)


@router.get("/students/{student_id}")
async def student_account_status(
    student_id: UUID,
    tenant_id=Depends(require_tenant_permission("accounts.manage")),
):
    return await get_student_account_status(tenant_id, student_id)


@router.post("/students/{student_id}")
async def student_account(
    student_id: UUID,
    payload: StudentAccountRequest = StudentAccountRequest(),
    tenant_id=Depends(require_tenant_permission("accounts.manage")),
):
    return await provision_student_account(tenant_id, student_id, payload.email)


@router.post("/students/{student_id}/resend-activation")
async def student_resend_activation(
    student_id: UUID,
    tenant_id=Depends(require_tenant_permission("accounts.manage")),
):
    return await resend_student_activation(tenant_id, student_id)
