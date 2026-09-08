from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from app.core.dependencies import require_tenant_permission
from app.modules.students.account_service import provision_guardian_account, provision_student_account

router = APIRouter(prefix="/student-accounts", tags=["Portal Accounts"])

class GuardianAccountRequest(BaseModel):
    email: EmailStr

class StudentAccountRequest(BaseModel):
    email: EmailStr | None = None

@router.post("/guardians/{guardian_id}")
async def guardian_account(guardian_id: UUID, payload: GuardianAccountRequest, tenant_id=Depends(require_tenant_permission("accounts.manage"))):
    return await provision_guardian_account(tenant_id, guardian_id, payload.email)

@router.post("/students/{student_id}")
async def student_account(student_id: UUID, payload: StudentAccountRequest = StudentAccountRequest(), tenant_id=Depends(require_tenant_permission("accounts.manage"))):
    return await provision_student_account(tenant_id, student_id, payload.email)
