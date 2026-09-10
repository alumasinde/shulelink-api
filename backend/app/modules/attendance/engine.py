import json
from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.core.database import get_pool


CAPTURE_STATUSES = {"present", "absent", "late", "half_day", "on_leave", "excused", "early_departure"}


def sid(value):
    return str(value) if value is not None else None


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def naive(value):
    return value.astimezone(timezone.utc).replace(tzinfo=None) if value and value.tzinfo else value


def evaluate_status(code: str, marked_at: datetime, scheduled_start_at: datetime | None, grace_minutes: int):
    """Return the effective status and late minutes for a captured attendance mark."""
    if code not in CAPTURE_STATUSES:
        raise HTTPException(422, f"Attendance status '{code}' cannot be used for attendance capture")
    if code not in {"present", "late"} or scheduled_start_at is None:
        return code, None
    minutes = max(0, int((marked_at - naive(scheduled_start_at)).total_seconds() // 60))
    if code == "present" and minutes > grace_minutes:
        return "late", minutes
    return code, (minutes if code == "late" else None)


async def exists(cur, table, tenant_id, item_id):
    await cur.execute(
        f"SELECT 1 FROM {table} WHERE id=%s AND tenant_id=%s LIMIT 1",
        (sid(item_id), sid(tenant_id)),
    )
    return await cur.fetchone() is not None


async def session_for_update(cur, tenant_id, session_id):
    await cur.execute(
        "SELECT id,academic_year_id,academic_term_id,class_level_id,stream_id,"
        "timetable_entry_id,session_type,session_date,scheduled_start_at,scheduled_end_at,"
        "actual_started_at,closed_at,status,attendance_policy_id "
        "FROM attendance_sessions WHERE id=%s AND tenant_id=%s FOR UPDATE",
        (sid(session_id), sid(tenant_id)),
    )
    return await cur.fetchone()


async def resolve_policy(cur, tenant_id, session):
    """Resolve the most specific active policy captured by the session."""
    await cur.execute(
        "SELECT id,grace_period_minutes FROM attendance_policies "
        "WHERE tenant_id=%s AND enabled=1 "
        "AND (effective_from IS NULL OR effective_from<=%s) "
        "AND (effective_to IS NULL OR effective_to>=%s) "
        "AND ((scope_type='stream' AND scope_id=%s) "
        "OR (scope_type='class' AND scope_id=%s) "
        "OR (scope_type='term' AND scope_id=%s) "
        "OR (scope_type='academic_year' AND scope_id=%s) "
        "OR (scope_type='school' AND scope_id IS NULL)) "
        "ORDER BY CASE scope_type WHEN 'stream' THEN 1 WHEN 'class' THEN 2 "
        "WHEN 'term' THEN 3 WHEN 'academic_year' THEN 4 ELSE 5 END, "
        "version DESC, created_at DESC LIMIT 1",
        (
            sid(tenant_id), session[7], session[7], sid(session[4]), sid(session[3]),
            sid(session[2]), sid(session[1]),
        ),
    )
    return await cur.fetchone()


async def validate_timetable_context(cur, tenant_id, payload):
    timetable_id = payload.get("timetable_entry_id")
    if not timetable_id:
        if payload.get("session_type") == "lesson":
            raise HTTPException(422, "Lesson attendance sessions require a timetable entry")
        return

    await cur.execute(
        "SELECT e.academic_year_id,e.academic_term_id,e.class_level_id,e.stream_id,"
        "e.day_of_week,p.start_time,p.end_time "
        "FROM timetable_entries e "
        "JOIN timetable_periods p ON p.id=e.period_id AND p.tenant_id=e.tenant_id "
        "WHERE e.id=%s AND e.tenant_id=%s LIMIT 1",
        (sid(timetable_id), sid(tenant_id)),
    )
    row = await cur.fetchone()
    if not row:
        raise HTTPException(404, "Timetable entry not found")

    if payload.get("academic_year_id") and sid(row[0]) != sid(payload["academic_year_id"]):
        raise HTTPException(400, "Timetable entry does not belong to the selected academic year")
    if payload.get("academic_term_id") and sid(row[1]) != sid(payload["academic_term_id"]):
        raise HTTPException(400, "Timetable entry does not belong to the selected academic term")
    if sid(row[2]) != sid(payload["class_level_id"]):
        raise HTTPException(400, "Timetable entry does not match the selected class")
    if sid(row[3]) != sid(payload.get("stream_id")):
        raise HTTPException(400, "Timetable entry does not match the selected stream")

    session_date = payload["session_date"]
    if isinstance(session_date, str):
        session_date = date.fromisoformat(session_date)
    if row[4] != session_date.isoweekday():
        raise HTTPException(400, "Timetable entry is not scheduled for the selected session date")

    scheduled_start = payload.get("scheduled_start_at")
    scheduled_end = payload.get("scheduled_end_at")
    if scheduled_start is not None and scheduled_end is not None:
        if scheduled_end <= scheduled_start:
            raise HTTPException(422, "scheduled_end_at must be after scheduled_start_at")


def serialize_result(result):
    return json.dumps(result, default=str, separators=(",", ":"))


async def create_session(tenant_id, user_id, payload):
    pool = get_pool()
    session_id = uuid4()
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                for table, key, label in [
                    ("academic_years", "academic_year_id", "Academic year"),
                    ("academic_terms", "academic_term_id", "Academic term"),
                    ("class_levels", "class_level_id", "Class level"),
                ]:
                    if payload.get(key) and not await exists(cur, table, tenant_id, payload[key]):
                        raise HTTPException(404, f"{label} not found")

                if payload.get("stream_id"):
                    await cur.execute(
                        "SELECT class_level_id FROM streams WHERE id=%s AND tenant_id=%s",
                        (sid(payload["stream_id"]), sid(tenant_id)),
                    )
                    row = await cur.fetchone()
                    if not row:
                        raise HTTPException(404, "Stream not found")
                    if sid(row[0]) != sid(payload["class_level_id"]):
                        raise HTTPException(400, "Stream does not belong to the selected class level")

                if payload.get("academic_term_id") and payload.get("academic_year_id"):
                    await cur.execute(
                        "SELECT academic_year_id FROM academic_terms WHERE id=%s AND tenant_id=%s",
                        (sid(payload["academic_term_id"]), sid(tenant_id)),
                    )
                    row = await cur.fetchone()
                    if not row or sid(row[0]) != sid(payload["academic_year_id"]):
                        raise HTTPException(400, "Academic term does not belong to the selected academic year")

                await validate_timetable_context(cur, tenant_id, payload)

                policy = await resolve_policy(
                    cur,
                    tenant_id,
                    [
                        None,
                        payload.get("academic_year_id"),
                        payload.get("academic_term_id"),
                        payload["class_level_id"],
                        payload.get("stream_id"),
                        payload.get("timetable_entry_id"),
                        payload["session_type"],
                        payload["session_date"],
                    ],
                )
                policy_id = policy[0] if policy else None

                await cur.execute(
                    "SELECT id FROM attendance_sessions WHERE tenant_id=%s AND session_date=%s "
                    "AND session_type=%s AND (class_level_id <=> %s) AND (stream_id <=> %s) "
                    "AND (timetable_entry_id <=> %s) AND status<>'cancelled' LIMIT 1",
                    (
                        sid(tenant_id), payload["session_date"], payload["session_type"],
                        sid(payload["class_level_id"]), sid(payload.get("stream_id")),
                        sid(payload.get("timetable_entry_id")),
                    ),
                )
                if await cur.fetchone():
                    raise HTTPException(409, "An attendance session already exists for this class, date and lesson")

                actual_started_at = naive(payload.get("actual_started_at")) if payload.get("actual_started_at") else utcnow()
                await cur.execute(
                    "INSERT INTO attendance_sessions "
                    "(id,tenant_id,academic_year_id,academic_term_id,class_level_id,stream_id,timetable_entry_id,"
                    "session_type,session_date,scheduled_start_at,scheduled_end_at,actual_started_at,status,"
                    "attendance_policy_id,opened_by_user_id,notes) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'open',%s,%s,%s)",
                    (
                        sid(session_id), sid(tenant_id), sid(payload.get("academic_year_id")),
                        sid(payload.get("academic_term_id")), sid(payload["class_level_id"]),
                        sid(payload.get("stream_id")), sid(payload.get("timetable_entry_id")),
                        payload["session_type"], payload["session_date"],
                        naive(payload.get("scheduled_start_at")), naive(payload.get("scheduled_end_at")),
                        actual_started_at, sid(policy_id), sid(user_id), payload.get("notes"),
                    ),
                )
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
    return session_id


async def get_session(tenant_id, session_id):
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id,academic_year_id,academic_term_id,class_level_id,stream_id,timetable_entry_id,"
                "session_type,session_date,scheduled_start_at,scheduled_end_at,actual_started_at,closed_at,status,attendance_policy_id "
                "FROM attendance_sessions WHERE id=%s AND tenant_id=%s",
                (sid(session_id), sid(tenant_id)),
            )
            row = await cur.fetchone()
            if not row:
                raise HTTPException(404, "Attendance session not found")
            await cur.execute(
                "SELECT COUNT(*) FROM student_enrollments WHERE tenant_id=%s AND class_level_id=%s "
                "AND (stream_id <=> %s) AND enrollment_date<=%s AND (exit_date IS NULL OR exit_date>=%s) "
                "AND status='active'",
                (sid(tenant_id), sid(row[3]), sid(row[4]), row[7], row[7]),
            )
            roster_count = (await cur.fetchone())[0]
            await cur.execute(
                "SELECT COUNT(*) FROM attendance_records WHERE tenant_id=%s AND session_id=%s",
                (sid(tenant_id), sid(session_id)),
            )
            marked_count = (await cur.fetchone())[0]

    keys = [
        "id", "academic_year_id", "academic_term_id", "class_level_id", "stream_id",
        "timetable_entry_id", "session_type", "session_date", "scheduled_start_at",
        "scheduled_end_at", "actual_started_at", "closed_at", "status", "attendance_policy_id",
    ]
    result = dict(zip(keys, row))
    result.update(roster_count=roster_count, marked_count=marked_count)
    return result


async def roster(tenant_id, session_id):
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT class_level_id,stream_id,session_date FROM attendance_sessions "
                "WHERE id=%s AND tenant_id=%s",
                (sid(session_id), sid(tenant_id)),
            )
            session = await cur.fetchone()
            if not session:
                raise HTTPException(404, "Attendance session not found")
            await cur.execute(
                "SELECT e.id,e.student_id,e.class_level_id,e.stream_id,st.admission_number,st.first_name,"
                "st.middle_name,st.last_name,COALESCE(a.code,'not_marked'),COALESCE(a.name,'Not Marked'),"
                "ar.late_minutes,ar.marked_at,ar.remarks "
                "FROM student_enrollments e "
                "JOIN students st ON st.id=e.student_id AND st.tenant_id=e.tenant_id "
                "LEFT JOIN attendance_records ar ON ar.session_id=%s AND ar.student_id=e.student_id AND ar.tenant_id=%s "
                "LEFT JOIN attendance_statuses a ON a.id=ar.attendance_status_id AND a.tenant_id=ar.tenant_id "
                "WHERE e.tenant_id=%s AND e.class_level_id=%s AND (e.stream_id <=> %s) "
                "AND e.enrollment_date<=%s AND (e.exit_date IS NULL OR e.exit_date>=%s) AND e.status='active' "
                "ORDER BY st.last_name,st.first_name,st.admission_number",
                (
                    sid(session_id), sid(tenant_id), sid(tenant_id), sid(session[0]), sid(session[1]),
                    session[2], session[2],
                ),
            )
            rows = await cur.fetchall()
    keys = [
        "enrollment_id", "student_id", "class_level_id", "stream_id", "admission_number",
        "first_name", "middle_name", "last_name", "status_code", "status_name", "late_minutes",
        "marked_at", "remarks",
    ]
    return [dict(zip(keys, row)) for row in rows]


async def mark(tenant_id, user_id, session_id, payload, idempotency_key):
    key = idempotency_key.strip() if idempotency_key else None
    if key and not 1 <= len(key) <= 191:
        raise HTTPException(422, "X-Idempotency-Key must contain 1-191 characters")

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                session = await session_for_update(cur, tenant_id, session_id)
                if not session:
                    raise HTTPException(404, "Attendance session not found")
                if session[12] != "open":
                    raise HTTPException(409, f"Attendance session is {session[12]} and cannot be modified")

                if key:
                    await cur.execute(
                        "SELECT payload_json FROM attendance_events "
                        "WHERE tenant_id=%s AND idempotency_key=%s LIMIT 1 FOR UPDATE",
                        (sid(tenant_id), key),
                    )
                    event = await cur.fetchone()
                    if event:
                        if event[0]:
                            return_payload = json.loads(event[0]) if isinstance(event[0], str) else event[0]
                            await conn.commit()
                            return return_payload
                        await conn.commit()
                        return {"session_id": session_id, "processed": 0, "created": 0, "updated": 0, "results": []}

                student_ids = [sid(item.student_id) for item in payload.items]
                placeholders = ",".join(["%s"] * len(student_ids))
                await cur.execute(
                    f"SELECT student_id FROM student_enrollments WHERE tenant_id=%s AND class_level_id=%s "
                    f"AND (stream_id <=> %s) AND enrollment_date<=%s AND (exit_date IS NULL OR exit_date>=%s) "
                    f"AND status='active' AND student_id IN ({placeholders})",
                    [
                        sid(tenant_id), sid(session[3]), sid(session[4]), session[7], session[7],
                        *student_ids,
                    ],
                )
                valid_students = {sid(row[0]) for row in await cur.fetchall()}
                if len(valid_students) != len(set(student_ids)):
                    raise HTTPException(422, "One or more students are not enrolled in this session's class/stream on the session date")

                created = 0
                results = []
                for item in payload.items:
                    await cur.execute(
                        "SELECT id,attendance_status_id,ast.code FROM attendance_records ar "
                        "JOIN attendance_statuses ast ON ast.id=ar.attendance_status_id AND ast.tenant_id=ar.tenant_id "
                        "WHERE ar.tenant_id=%s AND ar.session_id=%s AND ar.student_id=%s FOR UPDATE",
                        (sid(tenant_id), sid(session_id), sid(item.student_id)),
                    )
                    existing = await cur.fetchone()
                    if existing:
                        raise HTTPException(
                            409,
                            "Attendance is already recorded for one or more selected students; use the correction workflow to change an existing record",
                        )

                    await cur.execute(
                        "SELECT id,code FROM attendance_statuses WHERE tenant_id=%s AND code=%s AND is_active=1 LIMIT 1",
                        (sid(tenant_id), item.status_code),
                    )
                    status_row = await cur.fetchone()
                    if not status_row:
                        raise HTTPException(422, f"Attendance status '{item.status_code}' is not active")

                    marked_at = naive(item.marked_at or utcnow())
                    if marked_at > utcnow() + timedelta(minutes=5):
                        raise HTTPException(422, "marked_at cannot be materially in the future")

                    policy = await resolve_policy(cur, tenant_id, session)
                    grace = int(policy[1]) if policy else 0
                    code, late_minutes = evaluate_status(
                        status_row[1], marked_at, session[8], grace
                    )
                    if code != status_row[1]:
                        await cur.execute(
                            "SELECT id FROM attendance_statuses WHERE tenant_id=%s AND code=%s AND is_active=1 LIMIT 1",
                            (sid(tenant_id), code),
                        )
                        status_row = await cur.fetchone()
                        if not status_row:
                            raise HTTPException(500, "Configured attendance status catalog is incomplete")

                    record_id = uuid4()
                    await cur.execute(
                        "INSERT INTO attendance_records "
                        "(id,tenant_id,session_id,student_id,attendance_status_id,marked_at,marked_by_user_id,"
                        "source,late_minutes,remarks,is_correction) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0)",
                        (
                            sid(record_id), sid(tenant_id), sid(session_id), sid(item.student_id), sid(status_row[0]),
                            marked_at, sid(user_id), payload.source, late_minutes, item.remarks,
                        ),
                    )
                    created += 1
                    results.append(
                        {
                            "student_id": item.student_id,
                            "status_code": code,
                            "late_minutes": late_minutes,
                            "record_id": record_id,
                        }
                    )

                result = {
                    "session_id": session_id,
                    "processed": len(results),
                    "created": created,
                    "updated": 0,
                    "results": results,
                }
                await cur.execute(
                    "INSERT INTO attendance_events "
                    "(id,tenant_id,session_id,event_type,source,occurred_at,actor_user_id,idempotency_key,payload_json) "
                    "VALUES (%s,%s,%s,'captured',%s,%s,%s,%s,%s)",
                    (
                        sid(uuid4()), sid(tenant_id), sid(session_id), payload.source, utcnow(), sid(user_id),
                        key, serialize_result(result),
                    ),
                )
            await conn.commit()
            return result
        except Exception:
            await conn.rollback()
            raise


async def close(tenant_id, user_id, session_id):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                session = await session_for_update(cur, tenant_id, session_id)
                if not session:
                    raise HTTPException(404, "Attendance session not found")
                if session[12] != "open":
                    raise HTTPException(409, f"Attendance session is already {session[12]}")
                now = utcnow()
                await cur.execute(
                    "UPDATE attendance_sessions SET status='closed',closed_at=%s,closed_by_user_id=%s "
                    "WHERE id=%s AND tenant_id=%s",
                    (now, sid(user_id), sid(session_id), sid(tenant_id)),
                )
            await conn.commit()
            return {"id": session_id, "status": "closed", "closed_at": now}
        except Exception:
            await conn.rollback()
            raise
