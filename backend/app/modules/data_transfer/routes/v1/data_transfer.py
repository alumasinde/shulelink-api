from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from uuid import UUID

from app.core.dependencies import require_tenant_permission
from app.modules.data_transfer.school_structure import build_export, build_template, import_workbook, _fetch_rows

router = APIRouter(prefix="/data-transfer", tags=["Data Transfer"])


@router.get("/school-structure/template")
async def school_structure_template(
    tenant_id: UUID = Depends(require_tenant_permission("school.structure.manage")),
):
    del tenant_id
    output = build_template()
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="ShuleLink_School_Structure_Template.xlsx"'},
    )


@router.get("/school-structure/export")
async def school_structure_export(
    tenant_id: UUID = Depends(require_tenant_permission("school.structure.read")),
):
    output = build_export(await _fetch_rows(tenant_id))
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="ShuleLink_School_Structure_Export.xlsx"'},
    )


@router.post("/school-structure/import")
async def school_structure_import(
    file: UploadFile = File(...),
    mode: str = Query("create", pattern="^(create|upsert)$"),
    tenant_id: UUID = Depends(require_tenant_permission("school.structure.manage")),
):
    filename = (file.filename or "").lower()
    if not filename.endswith(".xlsx"):
        raise HTTPException(400, "Only .xlsx Excel files are supported")
    content = await file.read()
    result = await import_workbook(tenant_id, content, mode)
    return result
