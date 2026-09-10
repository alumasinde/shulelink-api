from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.core.database import get_pool


def sid(value):
    return str(value) if value is not None else None


def now_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def request_correction(tenant_id, user_id, record_id, new_status_code, reason):
    reason = reason.strip()
    if len(reason) < 3:
        raise HTTPException(422, "A correction reason must contain at least 3 characters")
    pool = get_pool()
    correction_id = uuid4()
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT ar.id,ar.session_id,ar.student_id,ar.attendance_status_id,s.status,ar.marked_at "
                    "FROM attendance_records ar JOIN attendance_sessions s ON s.id=ar.session_id AND s.tenant_id=ar.tenant_id "
                    "WHERE ar.id=%s AND ar.tenant_id=%s FOR UPDATE",
                    (sid(record_id), sid(tenant_id)),
                )
                record = await cur.fetchone()
                if not record:
                    raise HTTPException(404, "Attendance record not found")
                if record[4] == "cancelled":
                    raise HTTPException(409, "Attendance records from a cancelled session cannot be corrected")
                await cur.execute(
                    "SELECT id FROM attendance_statuses WHERE tenant_id=%s AND code=%s AND is_active=1 LIMIT 1",
                    (sid(tenant_id), new_status_code.strip().lower()),
                )
                new_status = await cur.fetchone()
                if not new_status or new_status[0] is None:
                    raise HTTPException(422, "The requested attendance status is not active")
                await cur.execute(
                    "SELECT code FROM attendance_statuses WHERE id=%s AND tenant_id=%s LIMIT 1",
                    (sid(record[3]), sid(tenant_id)),
                )
                previous = await cur.fetchone()
                if previous and previous[0] == new_status_code.strip().lower():
                    raise HTTPException(409, "The attendance record already has this status")
                await cur.execute(
                    "SELECT id FROM attendance_corrections WHERE tenant_id=%s AND attendance_record_id=%s "
                    "AND status IN ('pending','approved') LIMIT 1 FOR UPDATE",
                    (sid(tenant_id), sid(record_id)),
                )
                if await cur.fetchone():
                    raise HTTPException(409, "This attendance record already has an active correction request")
                await cur.execute(
                    "INSERT INTO attendance_corrections "
                    "(id,tenant_id,attendance_record_id,previous_status_id,new_status_id,reason,requested_by_user_id,status) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,'pending')",
                    (sid(correction_id), sid(tenant_id), sid(record_id), sid(record[3]), sid(new_status[0]), reason, sid(user_id)),
                )
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
    return await get_correction(tenant_id, correction_id)


async def get_correction(tenant_id, correction_id):
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT c.id,c.attendance_record_id,c.previous_status_id,ps.code,c.new_status_id,ns.code,c.reason,"
                "c.requested_by_user_id,c.approved_by_user_id,c.status,c.requested_at,c.approved_at,c.resolved_at "
                "FROM attendance_corrections c "
                "LEFT JOIN attendance_statuses ps ON ps.id=c.previous_status_id AND ps.tenant_id=c.tenant_id "
                "JOIN attendance_statuses ns ON ns.id=c.new_status_id AND ns.tenant_id=c.tenant_id "
                "WHERE c.id=%s AND c.tenant_id=%s",
                (sid(correction_id), sid(tenant_id)),
            )
            row = await cur.fetchone()
            if not row:
                raise HTTPException(404, "Attendance correction not found")
    keys = ["id","attendance_record_id","previous_status_id","previous_status_code","new_status_id","new_status_code","reason","requested_by_user_id","approved_by_user_id","status","requested_at","approved_at","resolved_at"]
    return dict(zip(keys, row))


async def list_corrections(tenant_id, status_filter=None, limit=100):
    limit = min(max(int(limit), 1), 200)
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            params = [sid(tenant_id)]
            sql = (
                "SELECT c.id,c.attendance_record_id,c.previous_status_id,ps.code,c.new_status_id,ns.code,c.reason,"
                "c.requested_by_user_id,c.approved_by_user_id,c.status,c.requested_at,c.approved_at,c.resolved_at "
                "FROM attendance_corrections c "
                "LEFT JOIN attendance_statuses ps ON ps.id=c.previous_status_id AND ps.tenant_id=c.tenant_id "
                "JOIN attendance_statuses ns ON ns.id=c.new_status_id AND ns.tenant_id=c.tenant_id "
                "WHERE c.tenant_id=%s"
            )
            if status_filter:
                sql += " AND c.status=%s"
                params.append(status_filter)
            sql += " ORDER BY c.requested_at DESC LIMIT %s"
            params.append(limit)
            await cur.execute(sql, params)
            rows = await cur.fetchall()
    keys = ["id","attendance_record_id","previous_status_id","previous_status_code","new_status_id","new_status_code","reason","requested_by_user_id","approved_by_user_id","status","requested_at","approved_at","resolved_at"]
    return [dict(zip(keys, row)) for row in rows]


async def resolve_correction(tenant_id, user_id, correction_id, approve):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT c.id,c.attendance_record_id,c.new_status_id,c.requested_by_user_id,c.status,ar.session_id,"
                    "ar.student_id,ar.attendance_status_id,ar.marked_at,s.scheduled_start_at,s.attendance_policy_id,s.status "
                    "FROM attendance_corrections c "
                    "JOIN attendance_records ar ON ar.id=c.attendance_record_id AND ar.tenant_id=c.tenant_id "
                    "JOIN attendance_sessions s ON s.id=ar.session_id AND s.tenant_id=ar.tenant_id "
                    "WHERE c.id=%s AND c.tenant_id=%s FOR UPDATE",
                    (sid(correction_id), sid(tenant_id)),
                )
                correction = await cur.fetchone()
                if not correction:
                    raise HTTPException(404, "Attendance correction not found")
                if correction[4] != "pending":
                    raise HTTPException(409, f"Attendance correction is already {correction[4]}")
                if sid(correction[3]) == sid(user_id):
                    raise HTTPException(403, "A correction requester cannot approve their own correction")
                resolved = now_utc()
                if not approve:
                    await cur.execute(
                        "UPDATE attendance_corrections SET status='rejected',approved_by_user_id=%s,approved_at=%s,resolved_at=%s "
                        "WHERE id=%s AND tenant_id=%s AND status='pending'",
                        (sid(user_id), resolved, resolved, sid(correction_id), sid(tenant_id)),
                    )
                    await cur.execute(
                        "INSERT INTO attendance_events (id,tenant_id,session_id,student_id,attendance_record_id,event_type,source,occurred_at,actor_user_id,payload_json) "
                        "VALUES (%s,%s,%s,%s,%s,'correction_rejected','manual',%s,%s,%s)",
                        (sid(uuid4()), sid(tenant_id), sid(correction[5]), sid(correction[6]), sid(correction[1]), resolved, sid(user_id), '{"status":"rejected"}'),
                    )
                else:
                    await cur.execute(
                        "SELECT code FROM attendance_statuses WHERE id=%s AND tenant_id=%s AND is_active=1 LIMIT 1",
                        (sid(correction[2]), sid(tenant_id)),
                    )
                    new_status = await cur.fetchone()
                    if not new_status:
                        raise HTTPException(409, "The requested correction status is no longer active")
                    await cur.execute(
                        "SELECT id FROM attendance_corrections WHERE tenant_id=%s AND attendance_record_id=%s "
                        "AND id<>%s AND status IN ('pending','approved') LIMIT 1",
                        (sid(tenant_id), sid(correction[1]), sid(correction_id)),
                    )
                    if await cur.fetchone():
                        raise HTTPException(409, "Another active correction exists for this attendance record")
                    late_minutes = None
                    if new_status[0] == "late" and correction[9] and correction[8]:
                        await cur.execute(
                            "SELECT grace_period_minutes FROM attendance_policies WHERE id=%s AND tenant_id=%s LIMIT 1",
                            (sid(correction[10]), sid(tenant_id)),
                        )
                        policy = await cur.fetchone()
                        grace = int(policy[0]) if policy else 0
                        late_minutes = max(0, int((correction[8] - correction[9]).total_seconds() // 60))
                        if late_minutes <= grace:
                            raise HTTPException(422, "The record time falls within the configured grace period and cannot be corrected to late")
                    await cur.execute(
                        "UPDATE attendance_records SET attendance_status_id=%s,late_minutes=%s,is_correction=1,updated_at=CURRENT_TIMESTAMP "
                        "WHERE id=%s AND tenant_id=%s",
                        (sid(correction[2]), late_minutes, sid(correction[1]), sid(tenant_id)),
                    )
                    await cur.execute(
                        "UPDATE attendance_corrections SET status='applied',approved_by_user_id=%s,approved_at=%s,resolved_at=%s "
                        "WHERE id=%s AND tenant_id=%s AND status='pending'",
                        (sid(user_id), resolved, resolved, sid(correction_id), sid(tenant_id)),
                    )
                    payload = '{"status":"applied"}'
                    await cur.execute(
                        "INSERT INTO attendance_events (id,tenant_id,session_id,student_id,attendance_record_id,event_type,source,occurred_at,actor_user_id,payload_json) "
                        "VALUES (%s,%s,%s,%s,%s,'correction_applied','manual',%s,%s,%s)",
                        (sid(uuid4()), sid(tenant_id), sid(correction[5]), sid(correction[6]), sid(correction[1]), resolved, sid(user_id), payload),
                    )
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
    return await get_correction(tenant_id, correction_id)
