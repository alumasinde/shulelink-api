from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr

from app.core.dependencies import require_tenant_permission
from app.core.rate_limit import limiter
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
async def guardian_account_status(guardian_id: UUID, tenant_id=Depends(require_tenant_permission("accounts.manage"))):
    return await get_guardian_account_status(tenant_id, guardian_id)


@router.post("/guardians/{guardian_id}")
@limiter.limit("10/minute")
async def guardian_account(request: Request, guardian_id: UUID, payload: GuardianAccountRequest, tenant_id=Depends(require_tenant_permission("accounts.manage"))):
    return await provision_guardian_account(tenant_id, guardian_id, payload.email)


@router.post("/guardians/{guardian_id}/resend-activation")
@limiter.limit("5/minute")
async def guardian_resend_activation(request: Request, guardian_id: UUID, tenant_id=Depends(require_tenant_permission("accounts.manage"))):
    return await resend_guardian_activation(tenant_id, guardian_id)


@router.get("/students/{student_id}")
async def student_account_status(student_id: UUID, tenant_id=Depends(require_tenant_permission("accounts.manage"))):
    return await get_student_account_status(tenant_id, student_id)


@router.post("/students/{student_id}")
@limiter.limit("10/minute")
async def student_account(request: Request, student_id: UUID, payload: StudentAccountRequest = StudentAccountRequest(), tenant_id=Depends(require_tenant_permission("accounts.manage"))):
    return await provision_student_account(tenant_id, student_id, payload.email)


@router.post("/students/{student_id}/resend-activation")
@limiter.limit("5/minute")
async def student_resend_activation(request: Request, student_id: UUID, tenant_id=Depends(require_tenant_permission("accounts.manage"))):
    return await resend_student_activation(tenant_id, student_id)
