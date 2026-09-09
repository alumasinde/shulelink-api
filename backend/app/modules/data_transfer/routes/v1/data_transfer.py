from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl import load_workbook
from uuid import UUID

from app.core.database import get_pool
from app.core.dependencies import require_tenant_permission
from app.modules.data_transfer.academic_years import resolve_import_academic_year
from app.modules.data_transfer.school_structure import build_export, build_template, import_workbook, _fetch_rows
from app.modules.data_transfer.students import build_export as build_student_export, build_template as build_student_template, import_workbook as import_student_workbook, _export_rows as export_student_rows

router = APIRouter(prefix="/data-transfer", tags=["Data Transfer"])

XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


async def _normalize_student_import_academic_years(tenant_id: UUID, content: bytes) -> bytes:
    """Translate human-friendly four-digit academic years to stored names.

    For example, an Excel value of ``2026`` is resolved to the school's
    matching academic year record when its dates fall within calendar 2026,
    such as 2026-01-01 through 2026-11-30. Exact stored names are left alone.
    """
    workbook = load_workbook(BytesIO(content), read_only=False, data_only=False)
    try:
        if "Enrollments" not in workbook.sheetnames:
            return content

        sheet = workbook["Enrollments"]
        headers = [str(cell.value or "").strip().lower().replace(" (required)", "") for cell in sheet[1]]
        if "academic_year" not in headers:
            return content

        academic_year_column = headers.index("academic_year") + 1
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                resolved: dict[str, str] = {}
                for row in sheet.iter_rows(min_row=2):
                    value = row[academic_year_column - 1].value
                    raw = "" if value is None else str(value).strip()
                    if not (len(raw) == 4 and raw.isdigit()):
                        continue
                    if raw in resolved:
                        row[academic_year_column - 1].value = resolved[raw]
                        continue
                    name = await resolve_import_academic_year(cur, tenant_id, value)
                    if name:
                        resolved[raw] = name
                        row[academic_year_column - 1].value = name

        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        return output.getvalue()
    finally:
        workbook.close()


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
        content = await file.read()
        content = await _normalize_student_import_academic_years(tenant_id, content)
        return await import_student_workbook(tenant_id, content, mode)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
