from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from uuid import UUID

from app.core.dependencies import require_tenant_permission
from app.modules.data_transfer.school_structure import build_export, build_template, import_workbook, _fetch_rows
from app.modules.data_transfer.students import build_export as build_student_export, build_template as build_student_template, import_workbook as import_student_workbook, _export_rows as export_student_rows

router = APIRouter(prefix="/data-transfer", tags=["Data Transfer"])

XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/school-structure/template")
async def school_structure_template(tenant_id: UUID = Depends(require_tenant_permission("school.structure.manage"))):
    del tenant_id
    return StreamingResponse(build_template(), media_type=XLSX_MEDIA, headers={"Content-Disposition": 'attachment; filename="ShuleLink_School_Structure_Template.xlsx"'})


@router.get("/school-structure/export")
async def school_structure_export(tenant_id: UUID = Depends(require_tenant_permission("school.structure.read"))):
    return StreamingResponse(build_export(await _fetch_rows(tenant_id)), media_type=XLSX_MEDIA, headers={"Content-Disposition": 'attachment; filename="ShuleLink_School_Structure_Export.xlsx"'})


@router.post("/school-structure/import")
async def school_structure_import(file: UploadFile = File(...), mode: str = Query("create", pattern="^(create|upsert)$"), tenant_id: UUID = Depends(require_tenant_permission("school.structure.manage"))):
    if not (file.filename or "").lower().endswith(".xlsx"): raise HTTPException(400, "Only .xlsx Excel files are supported")
    result = await import_workbook(tenant_id, await file.read(), mode)
    return result


@router.get("/students/template")
async def students_template(tenant_id: UUID = Depends(require_tenant_permission("students.manage"))):
    del tenant_id
    return StreamingResponse(build_student_template(), media_type=XLSX_MEDIA, headers={"Content-Disposition": 'attachment; filename="ShuleLink_Students_Guardians_Template.xlsx"'})


@router.get("/students/export")
async def students_export(tenant_id: UUID = Depends(require_tenant_permission("students.read"))):
    return StreamingResponse(build_student_export(await export_student_rows(tenant_id)), media_type=XLSX_MEDIA, headers={"Content-Disposition": 'attachment; filename="ShuleLink_Students_Guardians_Export.xlsx"'})


@router.post("/students/import")
async def students_import(file: UploadFile = File(...), mode: str = Query("create", pattern="^(create|upsert)$"), tenant_id: UUID = Depends(require_tenant_permission("students.manage"))):
    if not (file.filename or "").lower().endswith(".xlsx"): raise HTTPException(400, "Only .xlsx Excel files are supported")
    try:
        return await import_student_workbook(tenant_id, await file.read(), mode)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
