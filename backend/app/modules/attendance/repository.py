from uuid import UUID, uuid4

from fastapi import HTTPException

from app.core.database import get_pool


def sid(value):
    return str(value) if value is not None else None


async def _exists(cur, table: str, tenant_id: UUID, item_id: UUID) -> bool:
    await cur.execute(f"SELECT 1 FROM {table} WHERE id=%s AND tenant_id=%s LIMIT 1", (sid(item_id), sid(tenant_id)))
    return await cur.fetchone() is not None


async def get_status(cur, tenant_id: UUID, code: str):
    await cur.execute(
        "SELECT id,code,name,description,category,is_system,is_active,sort_order "
        "FROM attendance_statuses WHERE tenant_id=%s AND code=%s LIMIT 1",
        (sid(tenant_id), code),
    )
    return await cur.fetchone()


async def get_policy(cur, tenant_id: UUID, session_date):
    await cur.execute(
        "SELECT id,grace_period_minutes FROM attendance_policies "
        "WHERE tenant_id=%s AND enabled=1 "
        "AND (effective_from IS NULL OR effective_from<=%s) "
        "AND (effective_to IS NULL OR effective_to>=%s) "
        "ORDER BY CASE scope_type WHEN 'stream' THEN 1 WHEN 'class' THEN 2 WHEN 'term' THEN 3 "
        "WHEN 'academic_year' THEN 4 ELSE 5 END, version DESC, created_at DESC LIMIT 1",
        (sid(tenant_id), session_date, session_date),
    )
    return await cur.fetchone()


async def get_session_for_update(cur, tenant_id: UUID, session_id: UUID):
    await cur.execute(
        "SELECT id,academic_year_id,academic_term_id,class_level_id,stream_id,timetable_entry_id,"
        "session_type,session_date,scheduled_start_at,scheduled_end_at,actual_started_at,closed_at,status,"
        "attendance_policy_id,opened_by_user_id,closed_by_user_id,notes "
        "FROM attendance_sessions WHERE id=%s AND tenant_id=%s FOR UPDATE",
        (sid(session_id), sid(tenant_id)),
    )
    return await cur.fetchone()


async def create_session(tenant_id: UUID, payload: dict, opened_by_user_id: UUID | None):
    pool = get_pool()
    session_id = uuid4()
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                if payload.get("academic_year_id") and not await _exists(cur, "academic_years", tenant_id, payload["academic_year_id"]):
                    raise HTTPException(404, "Academic year not found")
                if payload.get("academic_term_id") and not await _exists(cur, "academic_terms", tenant_id, payload["academic_term_id"]):
                    raise HTTPException(404, "Academic term not found")
                if not await _exists(cur, "class_levels", tenant_id, payload["class_level_id"]):
                    raise HTTPException(404, "Class level not found")
                if payload.get("stream_id"):
                    await cur.execute("SELECT class_level_id FROM streams WHERE id=%s AND tenant_id=%s", (sid(payload["stream_id"]), sid(tenant_id)))
                    row = await cur.fetchone()
                    if not row:
                        raise HTTPException(404, "Stream not found")
                    if sid(row[0]) != sid(payload["class_level_id"]):
                        raise HTTPException(400, "Stream does not belong to the selected class level")
                if payload.get("academic_term_id") and payload.get("academic_year_id"):
                    await cur.execute("SELECT academic_year_id FROM academic_terms WHERE id=%s AND tenant_id=%s", (sid(payload["academic_term_id"]), sid(tenant_id)))
                    row = await cur.fetchone()
                    if not row or sid(row[0]) != sid(payload["academic_year_id"]):
                        raise HTTPException(400, "Academic term does not belong to the selected academic year")
                if payload.get("timetable_entry_id"):
                    await cur.execute(
                        "SELECT academic_year_id,academic_term_id,class_level_id,stream_id FROM timetable_entries WHERE id=%s AND tenant_id=%s",
                        (sid(payload["timetable_entry_id"]), sid(tenant_id)),
                    )
                    row = await cur.fetchone()
                    if not row:
                        raise HTTPException(404, "Timetable entry not found")
                    if sid(row[2]) != sid(payload["class_level_id"]) or sid(row[3]) != sid(payload.get("stream_id")):
                        raise HTTPException(400, "Timetable entry does not match the selected class or stream")
                    if payload.get("academic_term_id") and sid(row[1]) != sid(payload["academic_term_id"]):
                        raise HTTPException(400, "Timetable entry does not belong to the selected academic term")
                    if payload.get("academic_year_id") and sid(row[0]) != sid(payload["academic_year_id"]):
                        raise HTTPException(400, "Timetable entry does not belong to the selected academic year")

                policy = await get_policy(cur, tenant_id, payload["session_date"])
                policy_id = policy[0] if policy else None
                await cur.execute(
                    "SELECT id FROM attendance_sessions WHERE tenant_id=%s AND session_date=%s "
                    "AND session_type=%s AND (class_level_id <=> %s) AND (stream_id <=> %s) "
                    "AND (timetable_entry_id <=> %s) AND status<>%s LIMIT 1",
                    (sid(tenant_id), payload["session_date"], payload["session_type"], sid(payload["class_level_id"]),
                     sid(payload.get("stream_id")), sid(payload.get("timetable_entry_id")), "cancelled"),
                )
                if await cur.fetchone():
                    raise HTTPException(409, "An attendance session already exists for this class, date and lesson")

                await cur.execute(
                    "INSERT INTO attendance_sessions "
                    "(id,tenant_id,academic_year_id,academic_term_id,class_level_id,stream_id,timetable_entry_id,"
                    "session_type,session_date,scheduled_start_at,scheduled_end_at,actual_started_at,status,attendance_policy_id,opened_by_user_id,notes) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (sid(session_id), sid(tenant_id), sid(payload.get("academic_year_id")), sid(payload.get("academic_term_id")),
                     sid(payload["class_level_id"]), sid(payload.get("stream_id")), sid(payload.get("timetable_entry_id")),
                     payload["session_type"], payload["session_date"], payload.get("scheduled_start_at"), payload.get("scheduled_end_at"),
                     payload.get("scheduled_start_at"), "open", sid(policy_id), sid(opened_by_user_id), payload.get("notes")),
                )
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
    return session_id


async def fetch_session(tenant_id: UUID, session_id: UUID):
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            row = await get_session_for_update(cur, tenant_id, session_id)
            if not row:
                return None
            await cur.execute("SELECT COUNT(*) FROM student_enrollments WHERE tenant_id=%s AND class_level_id=%s AND (stream_id <=> %s) AND enrollment_date<=%s AND (exit_date IS NULL OR exit_date>=%s) AND status='active'", (sid(tenant_id), sid(row[3]), sid(row[4]), row[7], row[7]))
            roster_count = (await cur.fetchone())[0]
            await cur.execute("SELECT COUNT(*) FROM attendance_records WHERE tenant_id=%s AND session_id=%s", (sid(tenant_id), sid(session_id)))
            marked_count = (await cur.fetchone())[0]
    keys = ["id","academic_year_id","academic_term_id","class_level_id","stream_id","timetable_entry_id","session_type","session_date","scheduled_start_at","scheduled_end_at","actual_started_at","closed_at","status","attendance_policy_id","opened_by_user_id","closed_by_user_id","notes"]
    result = dict(zip(keys, row))
    result.update(roster_count=roster_count, marked_count=marked_count)
    return result


async def fetch_roster(tenant_id: UUID, session_id: UUID):
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            session = await get_session_for_update(cur, tenant_id, session_id)
            if not session:
                raise HTTPException(404, "Attendance session not found")
            await cur.execute(
                "SELECT e.id,e.student_id,e.class_level_id,e.stream_id,s.admission_number,s.first_name,s.middle_name,s.last_name,"
                "COALESCE(ar.status_code,'not_marked'),COALESCE(ar.status_name,'Not Marked'),ar.late_minutes,ar.marked_at,ar.remarks "
                "FROM student_enrollments e JOIN students s ON s.id=e.student_id AND s.tenant_id=e.tenant_id "
                "LEFT JOIN (SELECT ar1.* FROM attendance_records ar1 JOIN attendance_statuses ast1 ON ast1.id=ar1.attendance_status_id "
                "WHERE ar1.session_id=%s AND ar1.tenant_id=%s) ar ON ar.student_id=e.student_id "
                "LEFT JOIN attendance_statuses ars ON ars.id=ar.attendance_status_id "
                "WHERE e.tenant_id=%s AND e.class_level_id=%s AND (e.stream_id <=> %s) "
                "AND e.enrollment_date<=%s AND (e.exit_date IS NULL OR e.exit_date>=%s) AND e.status='active' "
                "ORDER BY s.last_name,s.first_name,s.admission_number",
                (sid(session_id), sid(tenant_id), sid(tenant_id), sid(session[3]), sid(session[4]), session[7], session[7]),
            )
            rows = await cur.fetchall()
    return [dict(zip(["enrollment_id","student_id","class_level_id","stream_id","admission_number","first_name","middle_name","last_name","status_code","status_name","late_minutes","marked_at","remarks"], r)) for r in rows]
