from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from uuid import UUID, uuid4

from fastapi import HTTPException
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

from app.core.database import get_pool

MAX_ROWS_PER_SHEET = 5000
MAX_ERRORS = 200

SHEETS = {
    "Teachers": [
        "teacher_number", "first_name", "middle_name", "last_name", "gender",
        "phone", "email", "department", "employment_type", "employment_date",
        "status", "notes",
    ],
    "Teacher Subjects": ["teacher_number", "subject_1", "subject_2"],
}

DISPLAY_HEADERS = {
    "teacher_number": "teacher_number (REQUIRED)",
    "first_name": "first_name (REQUIRED)",
    "middle_name": "middle_name",
    "last_name": "last_name (REQUIRED)",
    "gender": "gender (REQUIRED)",
    "phone": "phone",
    "email": "email",
    "department": "department",
    "employment_type": "employment_type",
    "employment_date": "employment_date",
    "status": "status (REQUIRED)",
    "notes": "notes",
    "subject_1": "subject_1",
    "subject_2": "subject_2",
}


def _text(value, required=False):
    if value is None:
        if required:
            raise ValueError("value is required")
        return None
    value = str(value).strip()
    if required and not value:
        raise ValueError("value is required")
    return value or None


def _date(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        raise ValueError("must be a date in YYYY-MM-DD format")


def _header_key(value):
    return str(value or "").strip().lower().replace(" (required)", "")


def _read_sheet(ws, expected):
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [_header_key(x) for x in rows[0]]
    if headers != expected:
        raise ValueError(
            f"Invalid columns. Expected: {', '.join(DISPLAY_HEADERS.get(x, x) for x in expected)}"
        )
    if len(rows) - 1 > MAX_ROWS_PER_SHEET:
        raise ValueError(f"Maximum {MAX_ROWS_PER_SHEET} data rows allowed")
    result = []
    for row_number, values in enumerate(rows[1:], 2):
        if all(v is None or str(v).strip() == "" for v in values):
            continue
        result.append(
            (row_number, {expected[i]: values[i] if i < len(values) else None for i in range(len(expected))})
        )
    return result


def _parse(workbook):
    errors = []
    parsed = {}
    for sheet, expected in SHEETS.items():
        if sheet not in workbook.sheetnames:
            errors.append({"sheet": sheet, "row": 1, "field": "sheet", "message": "Required sheet is missing"})
            continue
        try:
            parsed[sheet] = _read_sheet(workbook[sheet], expected)
        except ValueError as exc:
            errors.append({"sheet": sheet, "row": 1, "field": "columns", "message": str(exc)})
    return parsed, errors


def _parse_teacher(row_no, row, errors):
    try:
        gender = _text(row["gender"], True).lower()
        if gender not in {"male", "female", "other", "unspecified"}:
            raise ValueError("gender must be male, female, other, or unspecified")
        status = _text(row["status"], True).lower()
        if status not in {"active", "inactive", "on_leave", "terminated"}:
            raise ValueError("status must be active, inactive, on_leave, or terminated")
        return {
            "teacher_number": _text(row["teacher_number"], True),
            "first_name": _text(row["first_name"], True),
            "middle_name": _text(row["middle_name"]),
            "last_name": _text(row["last_name"], True),
            "gender": gender,
            "phone": _text(row["phone"]),
            "email": _text(row["email"]),
            "department": _text(row["department"]),
            "employment_type": _text(row["employment_type"]),
            "employment_date": _date(row["employment_date"]),
            "status": status,
            "notes": _text(row["notes"]),
        }
    except ValueError as exc:
        errors.append({"sheet": "Teachers", "row": row_no, "field": "data", "message": str(exc)})
        return None


def _parse_subjects(row_no, row, errors):
    teacher_number = _text(row["teacher_number"], True)
    subjects = [_text(row["subject_1"]), _text(row["subject_2"])]
    subjects = [x for x in subjects if x]
    normalized = [" ".join(x.lower().split()) for x in subjects]
    if len(normalized) != len(set(normalized)):
        errors.append({"sheet": "Teacher Subjects", "row": row_no, "field": "subjects", "message": "The same subject cannot be assigned twice to one teacher"})
        return None
    if len(subjects) > 2:
        errors.append({"sheet": "Teacher Subjects", "row": row_no, "field": "subjects", "message": "A teacher can have at most two subjects"})
        return None
    return {"teacher_number": teacher_number, "subjects": subjects}


def _safe_excel(value):
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _style_sheet(ws):
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for col in ws.columns:
        letter = col[0].column_letter
        ws.column_dimensions[letter].width = min(max(max(len(str(c.value or "")) for c in col) + 2, 14), 42)


def build_template():
    wb = Workbook()
    wb.remove(wb.active)
    start = wb.create_sheet("START HERE")
    start.append(["ShuleLink Teachers & Subject Assignments", ""])
    start.append(["Purpose", "Create, update, and bulk-edit teachers and their configured teaching subjects using one workbook."])
    start.append(["Natural key", "teacher_number uniquely identifies a teacher within the school. Never change it unless you intend to create a new teacher in Create mode."])
    start.append(["Subject references", "Use the subject code or exact subject name configured in the school. subject_1 and subject_2 are limited to two subjects."])
    start.append(["Modes", "Create New rejects existing teacher numbers. Upsert updates matching teachers and replaces their subject configuration when a Teacher Subjects row is supplied."])
    start.append(["Safety", "Imports are validated before commit, are tenant-scoped, and never delete teachers. Empty subject cells in a supplied Teacher Subjects row intentionally clear that teacher's configured subjects."])
    start.column_dimensions["A"].width = 28
    start.column_dimensions["B"].width = 110
    for sheet, fields in SHEETS.items():
        ws = wb.create_sheet(sheet)
        ws.append([DISPLAY_HEADERS[x] for x in fields])
        _style_sheet(ws)
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


async def _fetch_rows(tenant_id: UUID):
    pool = get_pool()
    data = {"Teachers": [], "Teacher Subjects": []}
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """SELECT t.teacher_number,t.first_name,t.middle_name,t.last_name,t.gender,
                          t.phone,t.email,d.code,t.employment_type,t.employment_date,t.status,t.notes,t.id
                   FROM teachers t
                   LEFT JOIN departments d ON d.id=t.department_id AND d.tenant_id=t.tenant_id
                   WHERE t.tenant_id=%s
                   ORDER BY t.last_name,t.first_name,t.teacher_number""",
                (str(tenant_id),),
            )
            teachers = await cur.fetchall()
            await cur.execute(
                """SELECT t.teacher_number,s.code,s.name
                   FROM teacher_subjects ts
                   JOIN teachers t ON t.id=ts.teacher_id AND t.tenant_id=ts.tenant_id
                   JOIN subjects s ON s.id=ts.subject_id AND s.tenant_id=ts.tenant_id
                   WHERE ts.tenant_id=%s
                   ORDER BY t.teacher_number,s.name""",
                (str(tenant_id),),
            )
            subject_rows = await cur.fetchall()

    subject_map: dict[str, list[str]] = {}
    for teacher_number, code, name in subject_rows:
        subject_map.setdefault(str(teacher_number), []).append(str(code or name))

    for row in teachers:
        teacher_number = str(row[0])
        subjects = subject_map.get(teacher_number, [])[:2]
        data["Teachers"].append(row[:12])
        data["Teacher Subjects"].append((teacher_number, *subjects, *([None] * (2 - len(subjects)))))
    return data


def build_export(data):
    wb = Workbook()
    wb.remove(wb.active)
    start = wb.create_sheet("START HERE")
    start.append(["ShuleLink Teachers & Subject Assignments Export", ""])
    start.append(["Import-ready", "This export uses teacher_number and subject codes instead of database UUIDs and can be edited then re-imported."])
    start.column_dimensions["A"].width = 28
    start.column_dimensions["B"].width = 110
    for sheet, fields in SHEETS.items():
        ws = wb.create_sheet(sheet)
        ws.append([DISPLAY_HEADERS[x] for x in fields])
        for row in data.get(sheet, []):
            ws.append([_safe_excel(x) for x in row])
        _style_sheet(ws)
        if sheet == "Teachers":
            employment_col = fields.index("employment_date") + 1
            for cell in ws.iter_cols(min_col=employment_col, max_col=employment_col, min_row=2):
                for value in cell:
                    value.number_format = "yyyy-mm-dd"
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def _reference_key(value):
    return " ".join(str(value or "").strip().lower().split())


async def import_workbook(tenant_id: UUID, content: bytes, mode: str):
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "Import file is too large. Maximum size is 10 MB.")
    try:
        wb = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:
        raise HTTPException(400, "The uploaded file is not a valid Excel workbook.") from exc

    parsed, errors = _parse(wb)
    wb.close()
    teachers_by_number: dict[str, dict] = {}
    subject_rows: list[tuple[int, dict]] = []
    for row_no, raw in parsed.get("Teachers", []):
        item = _parse_teacher(row_no, raw, errors)
        if not item:
            continue
        key = _reference_key(item["teacher_number"])
        if key in teachers_by_number:
            errors.append({"sheet": "Teachers", "row": row_no, "field": "teacher_number", "message": f"Duplicate teacher_number '{item['teacher_number']}' in this import."})
        else:
            teachers_by_number[key] = item
        if len(errors) >= MAX_ERRORS:
            break

    for row_no, raw in parsed.get("Teacher Subjects", []):
        item = _parse_subjects(row_no, raw, errors)
        if item:
            subject_rows.append((row_no, item))
        if len(errors) >= MAX_ERRORS:
            break

    subject_by_teacher: dict[str, tuple[int, dict]] = {}
    for row_no, item in subject_rows:
        key = _reference_key(item["teacher_number"])
        if key in subject_by_teacher:
            errors.append({"sheet": "Teacher Subjects", "row": row_no, "field": "teacher_number", "message": f"Duplicate Teacher Subjects row for '{item['teacher_number']}'."})
        else:
            subject_by_teacher[key] = (row_no, item)

    if len(errors) >= MAX_ERRORS:
        return {"valid": False, "mode": mode, "errors": errors[:MAX_ERRORS], "error_count": len(errors), "created": 0, "updated": 0, "subject_assignments": 0}

    pool = get_pool()
    created = updated = subject_assignments = 0
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT id,code,name FROM departments WHERE tenant_id=%s AND is_active=1",
                    (str(tenant_id),),
                )
                department_rows = await cur.fetchall()
                dept_lookup: dict[str, str] = {}
                dept_ambiguous: set[str] = set()
                for row in department_rows:
                    for value in (row[1], row[2]):
                        key = _reference_key(value)
                        if not key:
                            continue
                        if key in dept_lookup and dept_lookup[key] != str(row[0]):
                            dept_ambiguous.add(key)
                        else:
                            dept_lookup[key] = str(row[0])

                await cur.execute(
                    "SELECT id,code,name,department_id FROM subjects WHERE tenant_id=%s AND is_active=1",
                    (str(tenant_id),),
                )
                subject_db_rows = await cur.fetchall()
                subject_lookup: dict[str, str] = {}
                subject_department: dict[str, str | None] = {}
                subject_ambiguous: set[str] = set()
                for row in subject_db_rows:
                    subject_id, code, name, department_id = str(row[0]), row[1], row[2], row[3]
                    subject_department[subject_id] = str(department_id) if department_id else None
                    for value in (code, name):
                        key = _reference_key(value)
                        if not key:
                            continue
                        if key in subject_lookup and subject_lookup[key] != subject_id:
                            subject_ambiguous.add(key)
                        else:
                            subject_lookup[key] = subject_id

                await cur.execute(
                    "SELECT id,teacher_number,department_id FROM teachers WHERE tenant_id=%s",
                    (str(tenant_id),),
                )
                existing_rows = await cur.fetchall()
                existing = {_reference_key(row[1]): (str(row[0]), str(row[2]) if row[2] else None) for row in existing_rows}

                teacher_db_ids: dict[str, str] = {}
                teacher_departments: dict[str, str | None] = {}

                for key, item in teachers_by_number.items():
                    existing_row = existing.get(key)
                    if mode == "create" and existing_row:
                        errors.append({"sheet": "Teachers", "row": 0, "field": "teacher_number", "message": f"Teacher '{item['teacher_number']}' already exists. Use Upsert to update it."})
                        continue

                    department_id = None
                    if item["department"]:
                        dkey = _reference_key(item["department"])
                        if dkey in dept_ambiguous:
                            errors.append({"sheet": "Teachers", "row": 0, "field": "department", "message": f"Department '{item['department']}' is ambiguous."})
                            continue
                        department_id = dept_lookup.get(dkey)
                        if not department_id:
                            errors.append({"sheet": "Teachers", "row": 0, "field": "department", "message": f"Department '{item['department']}' not found."})
                            continue

                    if existing_row:
                        teacher_id = existing_row[0]
                        await cur.execute(
                            """UPDATE teachers SET first_name=%s,middle_name=%s,last_name=%s,gender=%s,phone=%s,email=%s,
                               department_id=%s,employment_type=%s,employment_date=%s,status=%s,notes=%s
                               WHERE id=%s AND tenant_id=%s""",
                            (item["first_name"], item["middle_name"], item["last_name"], item["gender"], item["phone"], item["email"],
                             department_id, item["employment_type"], item["employment_date"], item["status"], item["notes"], teacher_id, str(tenant_id)),
                        )
                        updated += 1
                    else:
                        teacher_id = str(uuid4())
                        try:
                            await cur.execute(
                                """INSERT INTO teachers (id,tenant_id,teacher_number,first_name,middle_name,last_name,gender,phone,email,
                                   department_id,employment_type,employment_date,status,notes)
                                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                                (teacher_id, str(tenant_id), item["teacher_number"], item["first_name"], item["middle_name"], item["last_name"],
                                 item["gender"], item["phone"], item["email"], department_id, item["employment_type"], item["employment_date"],
                                 item["status"], item["notes"]),
                            )
                        except Exception as exc:
                            if getattr(exc, "args", [None])[0] == 1062:
                                errors.append({"sheet": "Teachers", "row": 0, "field": "teacher_number", "message": f"Teacher number '{item['teacher_number']}' already exists."})
                                continue
                            raise
                        created += 1

                    teacher_db_ids[key] = teacher_id
                    teacher_departments[key] = department_id

                if errors:
                    raise ValueError("Import validation failed")

                for row_no, item in subject_rows:
                    teacher_key = _reference_key(item["teacher_number"])
                    teacher_id = teacher_db_ids.get(teacher_key)
                    if not teacher_id:
                        errors.append({"sheet": "Teacher Subjects", "row": row_no, "field": "teacher_number", "message": f"Teacher '{item['teacher_number']}' must be present in the Teachers sheet or already exist in the school."})
                        continue
                    department_id = teacher_departments.get(teacher_key)
                    if item["subjects"] and not department_id:
                        errors.append({"sheet": "Teacher Subjects", "row": row_no, "field": "subjects", "message": f"Teacher '{item['teacher_number']}' must have a department before subjects can be assigned."})
                        continue

                    resolved_subjects: list[str] = []
                    for raw_subject in item["subjects"]:
                        skey = _reference_key(raw_subject)
                        if skey in subject_ambiguous:
                            errors.append({"sheet": "Teacher Subjects", "row": row_no, "field": "subjects", "message": f"Subject '{raw_subject}' is ambiguous. Use its unique code."})
                            continue
                        subject_id = subject_lookup.get(skey)
                        if not subject_id:
                            errors.append({"sheet": "Teacher Subjects", "row": row_no, "field": "subjects", "message": f"Subject '{raw_subject}' not found or inactive."})
                            continue
                        if subject_department.get(subject_id) != department_id:
                            errors.append({"sheet": "Teacher Subjects", "row": row_no, "field": "subjects", "message": f"Subject '{raw_subject}' does not belong to teacher '{item['teacher_number']}' department."})
                            continue
                        resolved_subjects.append(subject_id)

                    if errors:
                        continue
                    await cur.execute("DELETE FROM teacher_subjects WHERE tenant_id=%s AND teacher_id=%s", (str(tenant_id), teacher_id))
                    for subject_id in resolved_subjects:
                        await cur.execute(
                            "INSERT INTO teacher_subjects (id,tenant_id,teacher_id,subject_id) VALUES (%s,%s,%s,%s)",
                            (str(uuid4()), str(tenant_id), teacher_id, subject_id),
                        )
                    subject_assignments += len(resolved_subjects)

                if errors:
                    raise ValueError("Import validation failed")
            await conn.commit()
        except ValueError:
            await conn.rollback()
            return {"valid": False, "mode": mode, "errors": errors[:MAX_ERRORS], "error_count": len(errors), "created": 0, "updated": 0, "subject_assignments": 0}
        except Exception:
            await conn.rollback()
            raise

    return {"valid": True, "mode": mode, "errors": [], "error_count": 0, "created": created, "updated": updated, "subject_assignments": subject_assignments}
