from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from app.core.dependencies import Principal, get_current_principal, require_tenant_permission
from app.modules.students.schemas import *
from app.modules.students.service import *

router = APIRouter(prefix="/students", tags=["Students"])


async def require_read(tenant_id: UUID = Depends(require_tenant_permission("students.read"))):
    return tenant_id


async def require_manage(tenant_id: UUID = Depends(require_tenant_permission("students.manage"))):
    return tenant_id


async def require_enroll(tenant_id: UUID = Depends(require_tenant_permission("students.enroll"))):
    return tenant_id


async def require_documents(tenant_id: UUID = Depends(require_tenant_permission("students.documents"))):
    return tenant_id


@router.get("", response_model=list[StudentResponse])
async def students(tenant_id=Depends(require_read), search: str | None = Query(default=None, max_length=100), status: str | None = Query(default=None, pattern="^(active|inactive|graduated|transferred|withdrawn)$"), limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)):
    return await list_students(tenant_id, search, status, limit, offset)


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
async def create(payload: StudentCreate, tenant_id=Depends(require_manage)):
    return await create_student(tenant_id, payload.model_dump())


# Static collection routes must be registered before /{student_id}.
@router.get("/document-types", response_model=list[DocumentTypeResponse])
async def document_types(tenant_id=Depends(require_read)):
    return await list_document_types(tenant_id)


@router.post("/document-types", response_model=DocumentTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_document_type_route(payload: DocumentTypeCreate, tenant_id=Depends(require_documents)):
    return await create_document_type(tenant_id, payload.model_dump())


@router.get("/guardians", response_model=list[GuardianResponse])
async def all_guardians(tenant_id=Depends(require_read), search: str | None = Query(default=None, max_length=100), limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)):
    return await list_guardians(tenant_id, search, limit, offset)


@router.post("/guardians", response_model=GuardianResponse, status_code=status.HTTP_201_CREATED)
async def create_guardian_route(payload: GuardianCreate, tenant_id=Depends(require_manage)):
    return await create_guardian(tenant_id, payload.model_dump())


@router.get("/guardians/{guardian_id}", response_model=GuardianResponse)
async def guardian(guardian_id: UUID, tenant_id=Depends(require_read)):
    return await get_guardian(tenant_id, guardian_id)


@router.patch("/guardians/{guardian_id}", response_model=GuardianResponse)
async def update_guardian_route(guardian_id: UUID, payload: GuardianUpdate, tenant_id=Depends(require_manage)):
    return await update_guardian(tenant_id, guardian_id, payload.model_dump(exclude_unset=True))


@router.get("/{student_id}", response_model=StudentDetailResponse)
async def detail(student_id: UUID, tenant_id=Depends(require_read)):
    student = await get_student(tenant_id, student_id)
    student["guardians"] = await list_student_guardians(tenant_id, student_id)
    student["enrollments"] = await list_enrollments(tenant_id, student_id)
    student["documents"] = await list_documents(tenant_id, student_id)
    return student


@router.patch("/{student_id}", response_model=StudentResponse)
async def update(student_id: UUID, payload: StudentUpdate, tenant_id=Depends(require_manage)):
    return await update_student(tenant_id, student_id, payload.model_dump(exclude_unset=True))


@router.get("/{student_id}/guardians", response_model=list[StudentGuardianResponse])
async def guardians(student_id: UUID, tenant_id=Depends(require_read)):
    return await list_student_guardians(tenant_id, student_id)


@router.post("/{student_id}/guardians", response_model=StudentGuardianResponse, status_code=status.HTTP_201_CREATED)
async def link_guardian(student_id: UUID, payload: StudentGuardianCreate, tenant_id=Depends(require_manage)):
    return await add_student_guardian(tenant_id, student_id, payload.model_dump())


@router.delete("/{student_id}/guardians/{guardian_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_guardian(student_id: UUID, guardian_id: UUID, tenant_id=Depends(require_manage)):
    await remove_student_guardian(tenant_id, student_id, guardian_id)


@router.get("/{student_id}/enrollments", response_model=list[EnrollmentResponse])
async def enrollment_history(student_id: UUID, tenant_id=Depends(require_read)):
    return await list_enrollments(tenant_id, student_id)


@router.post("/{student_id}/enrollments", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def enroll(student_id: UUID, payload: EnrollmentCreate, tenant_id=Depends(require_enroll)):
    return await create_enrollment(tenant_id, student_id, payload.model_dump())


@router.patch("/{student_id}/enrollments/{enrollment_id}", response_model=EnrollmentResponse)
async def update_enrollment_route(student_id: UUID, enrollment_id: UUID, payload: EnrollmentUpdate, tenant_id=Depends(require_enroll)):
    return await update_enrollment(tenant_id, student_id, enrollment_id, payload.model_dump(exclude_unset=True))


@router.get("/{student_id}/documents", response_model=list[StudentDocumentResponse])
async def documents(student_id: UUID, tenant_id=Depends(require_documents)):
    return await list_documents(tenant_id, student_id)


@router.post("/{student_id}/documents", response_model=StudentDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(student_id: UUID, payload: StudentDocumentCreate, tenant_id=Depends(require_documents), principal: Principal = Depends(get_current_principal)):
    return await create_document(tenant_id, student_id, payload.model_dump(), principal.user_id)
