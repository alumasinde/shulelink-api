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
from app.modules.data_transfer.academics import build_export as build_academics_export, build_template as build_academics_template, import_workbook as import_academics_workbook, _fetch_rows as export_academics_rows

router = APIRouter(prefix="/data-transfer", tags=["Data Transfer"])

XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MAX_IMPORT_BYTES = 10 * 1024 * 1024
MAX_IMPORT_ERRORS = 200


def _reference_key(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _reference_candidates(rows):
    """Build a normalized name/code lookup and detect ambiguous aliases."""
    lookup: dict[str, str] = {}
    ambiguous: dict[str, set[str]] = {}
    for row in rows:
        record_id, code, name = str(row[0]), row[1], row[2]
        for value in (code, name):
            key = _reference_key(value)
            if not key:
                continue
            previous = lookup.get(key)
            if previous and previous != record_id:
                ambiguous.setdefault(key, {previous}).add(record_id)
            else:
                lookup[key] = record_id
    for key in ambiguous:
        lookup.pop(key, None)
    return lookup, ambiguous


def _alphabetic_stream_index(value: object) -> int | None:
    """Return zero-based index for A, B, ..., Z style stream aliases."""
    key = _reference_key(value)
    if key.startswith("stream "):
        key = key[7:].strip()
    if len(key) != 1 or not ("a" <= key <= "z"):
        return None
    return ord(key) - ord("a")


def _resolve_reference(value: object, lookup: dict[str, str], ambiguous: dict[str, set[str]], label: str, available: list[str]) -> str:
    raw = str(value or "").strip()
    key = _reference_key(raw)
    if not key:
        raise ValueError(f"{label} is required")
    if key in ambiguous:
        raise ValueError(f"{label} '{raw}' is ambiguous in this school configuration")
    resolved = lookup.get(key)
    if resolved:
        return resolved
    sample = ", ".join(available[:10])
    suffix = f" Available: {sample}" if sample else " No active records are configured."
    raise ValueError(f"{label} '{raw}' not found.{suffix}")


def _resolve_stream(value: object, rows) -> str:
    """Resolve a stream by code/name, or by conventional A/B/C ordinal alias.

    The ordinal alias is deliberately scoped to the selected class level and
    only applies when the supplied value is a single alphabetic letter.
    Thus A means the first configured stream for that class, B the second,
    etc.; it never crosses class-level boundaries.
    """
    lookup, ambiguous = _reference_candidates(rows)
    available = [str(row[2]) for row in rows]
    raw = str(value or "").strip()
    try:
        return _resolve_reference(raw, lookup, ambiguous, "Stream", available)
    except ValueError as original:
        index = _alphabetic_stream_index(raw)
        if index is None or index >= len(rows):
            raise original
        candidate = rows[index]
        return str(candidate[0])


async def _normalize_student_import_references(tenant_id: UUID, content: bytes) -> tuple[bytes, list[dict]]:
    """Preflight and normalize all school-structure references used by enrollment rows."""
    workbook = load_workbook(BytesIO(content), read_only=False, data_only=False)
    errors: list[dict] = []
    try:
        if "Enrollments" not in workbook.sheetnames:
            return content, errors

        sheet = workbook["Enrollments"]
        headers = [str(cell.value or "").strip().lower().replace(" (required)", "") for cell in sheet[1]]
        required_headers = {"student_admission_number", "academic_year", "class_level", "stream", "enrollment_date", "exit_date", "status"}
        if not required_headers.issubset(set(headers)):
            return content, errors

        columns = {name: headers.index(name) + 1 for name in headers}
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT id, code, name FROM class_levels WHERE tenant_id=%s AND is_active=1 ORDER BY level_order, name",
                    (str(tenant_id),),
                )
                class_rows = await cur.fetchall()
                class_lookup, class_ambiguous = _reference_candidates(class_rows)
                class_available = [str(row[2]) for row in class_rows]

                await cur.execute(
                    "SELECT id, code, name, class_level_id FROM streams WHERE tenant_id=%s AND is_active=1 ORDER BY class_level_id, name",
                    (str(tenant_id),),
                )
                stream_rows = await cur.fetchall()
                streams_by_class: dict[str, list] = {}
                for row in stream_rows:
                    streams_by_class.setdefault(str(row[3]), []).append(row)

                workbook_students: set[str] = set()
                if "Students" in workbook.sheetnames:
                    student_sheet = workbook["Students"]
                    student_headers = [str(cell.value or "").strip().lower().replace(" (required)", "") for cell in student_sheet[1]] if student_sheet.max_row else []
                    if "admission_number" in student_headers:
                        student_col = student_headers.index("admission_number") + 1
                        workbook_students = {
                            str(row[student_col - 1].value).strip()
                            for row in student_sheet.iter_rows(min_row=2)
                            if row[student_col - 1].value is not None and str(row[student_col - 1].value).strip()
                        }

                seen_enrollments: set[tuple[str, str]] = set()
                for row_no in range(2, sheet.max_row + 1):
                    values = {name: sheet.cell(row_no, col).value for name, col in columns.items()}
                    if not any(value is not None and str(value).strip() for value in values.values()):
                        continue

                    student_adm = str(values.get("student_admission_number") or "").strip()
                    if student_adm and student_adm not in workbook_students:
                        await cur.execute(
                            "SELECT id FROM students WHERE tenant_id=%s AND admission_number=%s",
                            (str(tenant_id), student_adm),
                        )
                        if not await cur.fetchone():
                            errors.append({"sheet": "Enrollments", "row": row_no, "message": f"Student '{student_adm}' not found in this import or school."})

                    try:
                        academic_year = await resolve_import_academic_year(cur, tenant_id, values.get("academic_year"))
                        if not academic_year:
                            raw_year = str(values.get("academic_year") or "").strip()
                            errors.append({"sheet": "Enrollments", "row": row_no, "message": f"Academic year '{raw_year}' not found in this school."})
                        else:
                            sheet.cell(row_no, columns["academic_year"]).value = academic_year
                    except ValueError as exc:
                        errors.append({"sheet": "Enrollments", "row": row_no, "message": str(exc)})

                    try:
                        class_id = _resolve_reference(values.get("class_level"), class_lookup, class_ambiguous, "Class level", class_available)
                        class_row = next(row for row in class_rows if str(row[0]) == class_id)
                        sheet.cell(row_no, columns["class_level"]).value = str(class_row[1])
                    except (ValueError, StopIteration) as exc:
                        errors.append({"sheet": "Enrollments", "row": row_no, "message": str(exc) or "Class level could not be resolved"})
                        class_id = None

                    if class_id:
                        class_stream_rows = streams_by_class.get(class_id, [])
                        stream_value = values.get("stream")
                        if stream_value is not None and str(stream_value).strip():
                            try:
                                stream_id = _resolve_stream(stream_value, class_stream_rows)
                                stream_row = next(row for row in class_stream_rows if str(row[0]) == stream_id)
                                sheet.cell(row_no, columns["stream"]).value = str(stream_row[1])
                            except (ValueError, StopIteration) as exc:
                                available = ", ".join(str(row[2]) for row in class_stream_rows[:10])
                                suffix = f" Available: {available}" if available else " No active streams are configured for this class level."
                                errors.append({"sheet": "Enrollments", "row": row_no, "message": f"{exc}{suffix}"})

                    status = str(values.get("status") or "active").strip().lower()
                    if status not in {"active", "completed", "withdrawn"}:
                        errors.append({"sheet": "Enrollments", "row": row_no, "message": f"Enrollment status '{status}' is invalid. Allowed: active, completed, withdrawn."})

                    start = values.get("enrollment_date")
                    end = values.get("exit_date")
                    if start and end:
                        try:
                            from datetime import date, datetime
                            start_date = start.date() if isinstance(start, datetime) else start if isinstance(start, date) else date.fromisoformat(str(start).strip())
                            end_date = end.date() if isinstance(end, datetime) else end if isinstance(end, date) else date.fromisoformat(str(end).strip())
                            if end_date < start_date:
                                errors.append({"sheet": "Enrollments", "row": row_no, "message": "exit_date cannot be before enrollment_date"})
                        except ValueError:
                            pass

                    normalized_year = str(sheet.cell(row_no, columns["academic_year"]).value or "").strip()
                    if student_adm and normalized_year:
                        duplicate_key = (_reference_key(student_adm), _reference_key(normalized_year))
                        if duplicate_key in seen_enrollments:
                            errors.append({"sheet": "Enrollments", "row": row_no, "message": f"Duplicate enrollment for student '{student_adm}' and academic year '{normalized_year}' in this import."})
                        seen_enrollments.add(duplicate_key)

        if errors:
            return content, errors[:MAX_IMPORT_ERRORS]

        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        return output.getvalue(), []
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
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(400, "Only .xlsx Excel files are supported")
    try:
        content = await file.read()
        if len(content) > MAX_IMPORT_BYTES:
            raise HTTPException(413, "Import file is too large. Maximum size is 10 MB.")
        content, reference_errors = await _normalize_student_import_references(tenant_id, content)
        if reference_errors:
            return {"valid": False, "mode": mode, "errors": reference_errors, "error_count": len(reference_errors), "created": 0, "updated": 0}
        return await import_student_workbook(tenant_id, content, mode)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/academics/teachers/template")
async def academics_teachers_template(tenant_id: UUID = Depends(require_tenant_permission("teachers.manage"))):
    del tenant_id
    return StreamingResponse(build_academics_template(), media_type=XLSX_MEDIA, headers={"Content-Disposition": 'attachment; filename="ShuleLink_Teachers_Subject_Assignments_Template.xlsx"'})


@router.get("/academics/teachers/export")
async def academics_teachers_export(tenant_id: UUID = Depends(require_tenant_permission("teachers.read"))):
    return StreamingResponse(build_academics_export(await export_academics_rows(tenant_id)), media_type=XLSX_MEDIA, headers={"Content-Disposition": 'attachment; filename="ShuleLink_Teachers_Subject_Assignments_Export.xlsx"'})


@router.post("/academics/teachers/import")
async def academics_teachers_import(file: UploadFile = File(...), mode: str = Query("create", pattern="^(create|upsert)$"), tenant_id: UUID = Depends(require_tenant_permission("teachers.manage"))):
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(400, "Only .xlsx Excel files are supported")
    content = await file.read()
    if len(content) > MAX_IMPORT_BYTES:
        raise HTTPException(413, "Import file is too large. Maximum size is 10 MB.")
    return await import_academics_workbook(tenant_id, content, mode)
