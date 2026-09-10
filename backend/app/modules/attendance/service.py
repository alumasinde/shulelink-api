from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.core.database import get_pool
from app.modules.attendance.repository import sid, get_policy, get_session_for_update, get_status, create_session, fetch_session, fetch_roster


STATUS_CODES = {"present", "absent", "late", "half_day", "on_leave", "excused", "early_departure", "not_marked"}


def _naive_utc(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


async def create_attendance_session(tenant_id: UUID, principal_user_id: UUID, payload: dict):
    session_id = await create_session(tenant_id, payload, principal_user_id)
    return await fetch_session(tenant_id, session_id)


async def get_attendance_session(tenant_id: UUID, session_id: UUID):
    result = await fetch_session(tenant_id, session_id)
    if not result:
        raise HTTPException(404, "Attendance session not found")
    return result


async def get_session_roster(tenant_id: UUID, session_id: UUID):
    return await fetch_roster(tenant_id, session_id)


async def _resolve_status_and_lateness(cur, tenant_id, session, item, source):
    status_code = item.status_code
    status = await get_status(cur, tenant_id, status_code)
    if not status or not status[5]:
        raise HTTPException(422, f"Attendance status '{status_code}' is not active")
    if status_code not in STATUS_CODES:
        raise HTTPException(422, f"Unsupported attendance status '{status_code}'")

    marked_at = _naive_utc(item.marked_at or datetime.now(timezone.utc))
    late_minutes = None
    if status_code == "present" and session[8] is not None:
        scheduled = _naive_utc(session[8])
        policy = await get_policy(cur, tenant_id, session[7])
        grace = int(policy[1]) if policy else 0
        if marked_at > scheduled + timedelta(minutes=grace):
            late_minutes = max(0, int((marked_at - scheduled).total_seconds() // 60))
            late_status = await get_status(cur, tenant_id, "late")
            if late_status and late_status[5] and late_status[6]:
                status = late_status
                status_code = "late"
    if status_code == "late":
        if session[8] is None:
            raise HTTPException(422, "Late attendance requires a scheduled session start time")
        scheduled = _naive_utc(session[8])
        late_minutes = max(0, int((marked_at - scheduled).total_seconds() // 60))
    if status_code != "late":
        late_minutes = None
    return status, marked_at, late_minutes


async def mark_attendance(tenant_id: UUID, principal_user_id: UUID, session_id: UUID, payload, idempotency_key: str | None):
    if idempotency_key is not None:
        idempotency_key = idempotency_key.strip()
        if not idempotency_key or len(idempotency_key) > 191:
            raise HTTPException(422, "X-Idempotency-Key must contain 1-191 characters")

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                session = await get_session_for_update(cur, tenant_id, session_id)
                if not session:
                    raise HTTPException(404, "Attendance session not found")
                if session[12] != "open":
                    raise HTTPException(409, f"Attendance session is {session[12]} and cannot be modified")

                # Validate every student against the session's dated enrollment before changing anything.
                student_ids = [sid(item.student_id) for item in payload.items]
                placeholders = ",".join(["%s"] * len(student_ids))
                await cur.execute(
                    f"SELECT e.student_id FROM student_enrollments e "
                    f"WHERE e.tenant_id=%s AND e.class_level_id=%s AND (e.stream_id <=> %s) "
                    f"AND e.enrollment_date<=%s AND (e.exit_date IS NULL OR e.exit_date>=%s) "
                    f"AND e.status='active' AND e.student_id IN ({placeholders})",
                    [sid(tenant_id), sid(session[3]), sid(session[4]), session[7], session[7], *student_ids],
                )
                valid_students = {sid(row[0]) for row in await cur.fetchall()}
                missing = [x for x in student_ids if x not in valid_students]
                if missing:
                    raise HTTPException(422, "One or more students are not enrolled in this session's class/stream on the session date")

                if idempotency_key:
                    await cur.execute(
                        "SELECT id FROM attendance_events WHERE tenant_id=%s AND idempotency_key=%s LIMIT 1 FOR UPDATE",
                        (sid(tenant_id), idempotency_key),
                    )
                    existing = await cur.fetchone()
                    if existing:
                        await conn.commit()
                        return {"session_id": session_id, "processed": 0, "created": 0, "updated": 0, "results": [], "idempotent_replay": True}

                results = []
                created = updated = 0
                event_id = uuid4()
                # The request is one atomic unit. If any item fails, none is persisted.
                for item in payload.items:
                    status, marked_at, late_minutes = await _resolve_status_and_lateness(cur, tenant_id, session, item, payload.source)
                    await cur.execute(
                        "SELECT ar.id,ar.attendance_status_id,ast.code FROM attendance_records ar "
                        "JOIN attendance_statuses ast ON ast.id=ar.attendance_status_id AND ast.tenant_id=ar.tenant_id "
                        "WHERE ar.tenant_id=%s AND ar.session_id=%s AND ar.student_id=%s FOR UPDATE",
                        (sid(tenant_id), sid(session_id), sid(item.student_id)),
                    )
                    existing_record = await cur.fetchone()
                    if existing_record:
                        if existing_record[2] == "not_marked" and item.status_code == "not_marked":
                            continue
                        await cur.execute(
                            "UPDATE attendance_records SET attendance_status_id=%s,marked_at=%s,marked_by_user_id=%s,source=%s,late_minutes=%s,remarks=%s,is_correction=%s "
                            "WHERE id=%s AND tenant_id=%s",
                            (sid(status[0]), marked_at, sid(principal_user_id), payload.source, late_minutes, item.remarks, 1 if existing_record[2] != status[1] else 0, sid(existing_record[0]), sid(tenant_id)),
                        )
                        updated += 1
                        record_id = existing_record[0]
                        event_type = "status_changed" if existing_record[1] != status[0] else "captured"
                    else:
                        record_id = uuid4()
                        await cur.execute(
                            "INSERT INTO attendance_records (id,tenant_id,session_id,student_id,attendance_status_id,marked_at,marked_by_user_id,source,late_minutes,remarks,is_correction) "
                            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0)",
                            (sid(record_id), sid(tenant_id), sid(session_id), sid(item.student_id), sid(status[0]), marked_at, sid(principal_user_id), payload.source, late_minutes, item.remarks),
                        )
                        created += 1
                        event_type = "captured"
                    results.append({"student_id": item.student_id, "status_code": status[1], "late_minutes": late_minutes, "record_id": record_id})

                await cur.execute(
                    "INSERT INTO attendance_events (id,tenant_id,session_id,event_type,source,occurred_at,actor_user_id,idempotency_key,payload_json) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (sid(event_id), sid(tenant_id), sid(session_id), "captured", payload.source, datetime.now(timezone.utc).replace(tzinfo=None), sid(principal_user_id), idempotency_key, None),
                )
            await conn.commit()
            return {"session_id": session_id, "processed": len(results), "created": created, "updated": updated, "results": results, "idempotent_replay": False}
        except Exception:
            await conn.rollback()
            raise


async def close_attendance_session(tenant_id: UUID, principal_user_id: UUID, session_id: UUID):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                session = await get_session_for_update(cur, tenant_id, session_id)
                if not session:
                    raise HTTPException(404, "Attendance session not found")
                if session[12] != "open":
                    raise HTTPException(409, f"Attendance session is already {session[12]}")
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                await cur.execute("UPDATE attendance_sessions SET status='closed',closed_at=%s,closed_by_user_id=%s WHERE id=%s AND tenant_id=%s", (now, sid(principal_user_id), sid(session_id), sid(tenant_id)))
            await conn.commit()
            return {"id": session_id, "status": "closed", "closed_at": now}
        except Exception:
            await conn.rollback()
            raise


async def list_attendance_statuses(tenant_id: UUID):
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id,code,name,description,category,is_system,is_active,sort_order FROM attendance_statuses WHERE tenant_id=%s ORDER BY sort_order,code", (sid(tenant_id),))
            rows = await cur.fetchall()
    keys = ["id","code","name","description","category","is_system","is_active","sort_order"]
    return [dict(zip(keys, row)) for row in rows]
