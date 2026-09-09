from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import HTTPException

from app.core.database import get_pool


def sid(value): return str(value) if value is not None else None


async def bulk_update_teachers(tenant_id: UUID, teacher_ids: list[UUID], changes: dict):
    ids = list(dict.fromkeys(sid(x) for x in teacher_ids))
    if not ids:
        raise HTTPException(422, "Select at least one teacher")
    if len(ids) > 500:
        raise HTTPException(422, "A maximum of 500 teachers can be edited at once")

    allowed = {"department_id", "employment_type", "status", "gender"}
    payload = {k: v for k, v in changes.items() if k in allowed}
    if not payload:
        raise HTTPException(422, "Select at least one field to update")

    pool = get_pool()
    placeholders = ",".join(["%s"] * len(ids))
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"SELECT id,department_id FROM teachers WHERE tenant_id=%s AND id IN ({placeholders}) FOR UPDATE",
                    [sid(tenant_id), *ids],
                )
                teacher_rows = await cur.fetchall()
                found = {sid(row[0]) for row in teacher_rows}
                if len(found) != len(ids):
                    raise HTTPException(404, "One or more selected teachers were not found")

                department_id = payload.get("department_id")
                if department_id is not None:
                    await cur.execute(
                        "SELECT id FROM departments WHERE tenant_id=%s AND id=%s AND is_active=1",
                        (sid(tenant_id), sid(department_id)),
                    )
                    if not await cur.fetchone():
                        raise HTTPException(404, "Department not found or inactive")

                set_parts = []
                args = []
                for key, value in payload.items():
                    set_parts.append(f"{key}=%s")
                    args.append(sid(value) if isinstance(value, UUID) else value)
                await cur.execute(
                    f"UPDATE teachers SET {', '.join(set_parts)} WHERE tenant_id=%s AND id IN ({placeholders})",
                    [*args, sid(tenant_id), *ids],
                )
                updated = cur.rowcount

                # Match the single-teacher edit rule: changing a department
                # invalidates previously configured subjects for that teacher.
                if department_id is not None:
                    changed_ids = [sid(row[0]) for row in teacher_rows if sid(row[1]) != sid(department_id)]
                    if changed_ids:
                        changed_marks = ",".join(["%s"] * len(changed_ids))
                        await cur.execute(
                            f"DELETE FROM teacher_subjects WHERE tenant_id=%s AND teacher_id IN ({changed_marks})",
                            [sid(tenant_id), *changed_ids],
                        )
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise

    return {"updated": updated, "teacher_ids": ids}


async def bulk_replace_teacher_subjects(tenant_id: UUID, teacher_ids: list[UUID], subject_ids: list[UUID]):
    teachers_ids = list(dict.fromkeys(sid(x) for x in teacher_ids))
    subjects_ids = list(dict.fromkeys(sid(x) for x in subject_ids))
    if not teachers_ids:
        raise HTTPException(422, "Select at least one teacher")
    if len(teachers_ids) > 500:
        raise HTTPException(422, "A maximum of 500 teachers can be updated at once")
    if not 1 <= len(subjects_ids) <= 2:
        raise HTTPException(422, "Select one or two subjects")

    pool = get_pool()
    teacher_marks = ",".join(["%s"] * len(teachers_ids))
    subject_marks = ",".join(["%s"] * len(subjects_ids))
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    f"SELECT id,department_id FROM teachers WHERE tenant_id=%s AND id IN ({teacher_marks}) FOR UPDATE",
                    [sid(tenant_id), *teachers_ids],
                )
                teacher_rows = await cur.fetchall()
                found = {sid(row[0]) for row in teacher_rows}
                if len(found) != len(teachers_ids):
                    raise HTTPException(404, "One or more selected teachers were not found")

                department_ids = {sid(row[1]) for row in teacher_rows if row[1] is not None}
                if len(department_ids) != 1 or any(row[1] is None for row in teacher_rows):
                    raise HTTPException(400, "Bulk subject assignment requires all selected teachers to have the same department")
                department_id = next(iter(department_ids))

                await cur.execute(
                    f"SELECT id FROM subjects WHERE tenant_id=%s AND department_id=%s AND is_active=1 AND id IN ({subject_marks})",
                    [sid(tenant_id), department_id, *subjects_ids],
                )
                valid = {sid(row[0]) for row in await cur.fetchall()}
                if valid != set(subjects_ids):
                    raise HTTPException(400, "Every selected subject must be active and belong to the selected teachers' department")

                await cur.execute(
                    f"DELETE FROM teacher_subjects WHERE tenant_id=%s AND teacher_id IN ({teacher_marks})",
                    [sid(tenant_id), *teachers_ids],
                )
                for teacher_id in teachers_ids:
                    for subject_id in subjects_ids:
                        await cur.execute(
                            "INSERT INTO teacher_subjects (id,tenant_id,teacher_id,subject_id) VALUES (%s,%s,%s,%s)",
                            (str(uuid4()), sid(tenant_id), teacher_id, subject_id),
                        )
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise

    return {"updated": len(teachers_ids), "teachers": len(teachers_ids), "subjects": len(subjects_ids)}
