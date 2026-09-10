from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException

from app.core.database import get_central_pool, get_pool

EXEMPTION_TYPES = {"leave", "sickbay", "suspension", "official_duty", "approved_absence"}
MANAGE_PERMISSIONS = {
    "leave": "attendance.leave.manage",
    "sickbay": "attendance.sickbay.manage",
    "suspension": "attendance.leave.manage",
    "official_duty": "attendance.leave.manage",
    "approved_absence": "attendance.leave.manage",
}


def sid(value):
    return str(value) if value is not None else None


def now_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _require_exemption_permission(tenant_id, user_id, exemption_type):
    permission = MANAGE_PERMISSIONS.get(exemption_type)
    if not permission:
        raise HTTPException(422, "Unsupported attendance exemption type")
    pool = get_central_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT 1 FROM tenant_memberships m "
                "JOIN tenant_membership_roles mr ON mr.membership_id=m.id "
                "JOIN tenant_roles r ON r.id=mr.role_id "
                "JOIN tenant_role_permissions rp ON rp.role_id=r.id "
                "JOIN tenant_permissions p ON p.id=rp.permission_id "
                "WHERE m.tenant_id=%s AND m.tenant_user_id=%s AND m.status='active' AND p.code=%s LIMIT 1",
                (sid(tenant_id), sid(user_id), permission),
            )
            if not await cur.fetchone():
                raise HTTPException(status_code=403, detail="Insufficient attendance exemption permission")


async def _student_exists(cur, tenant_id, student_id, lock=False):
    suffix = " FOR UPDATE" if lock else ""
    await cur.execute(
        f"SELECT 1 FROM students WHERE id=%s AND tenant_id=%s LIMIT 1{suffix}",
        (sid(student_id), sid(tenant_id)),
    )
    if not await cur.fetchone():
        raise HTTPException(404, "Student not found")


async def create_exemption(tenant_id, user_id, student_id, exemption_type, starts_at, ends_at, reason=None, source_type=None, source_id=None):
    exemption_type = exemption_type.strip().lower()
    if exemption_type not in EXEMPTION_TYPES:
        raise HTTPException(422, "Unsupported attendance exemption type")
    if ends_at <= starts_at:
        raise HTTPException(422, "ends_at must be after starts_at")
    await _require_exemption_permission(tenant_id, user_id, exemption_type)
    pool = get_pool()
    exemption_id = uuid4()
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                await _student_exists(cur, tenant_id, student_id, lock=True)
                await cur.execute(
                    "SELECT id FROM attendance_exemptions WHERE tenant_id=%s AND student_id=%s "
                    "AND status IN ('pending','approved') AND starts_at < %s AND ends_at > %s LIMIT 1",
                    (sid(tenant_id), sid(student_id), ends_at, starts_at),
                )
                if await cur.fetchone():
                    raise HTTPException(409, "The student already has an overlapping leave or exemption")
                await cur.execute(
                    "INSERT INTO attendance_exemptions "
                    "(id,tenant_id,student_id,exemption_type,status,starts_at,ends_at,reason,source_type,source_id,created_by_user_id,requested_by_user_id) "
                    "VALUES (%s,%s,%s,%s,'pending',%s,%s,%s,%s,%s,%s,%s)",
                    (sid(exemption_id), sid(tenant_id), sid(student_id), exemption_type, starts_at, ends_at, reason, source_type, sid(source_id), sid(user_id), sid(user_id)),
                )
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
    return await get_exemption(tenant_id, exemption_id)


async def get_exemption(tenant_id, exemption_id):
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id,student_id,exemption_type,status,starts_at,ends_at,reason,source_type,source_id,"
                "created_by_user_id,requested_by_user_id,approved_by_user_id,approved_at,resolved_at "
                "FROM attendance_exemptions WHERE id=%s AND tenant_id=%s",
                (sid(exemption_id), sid(tenant_id)),
            )
            row = await cur.fetchone()
            if not row:
                raise HTTPException(404, "Attendance exemption not found")
    keys = ["id","student_id","exemption_type","status","starts_at","ends_at","reason","source_type","source_id","created_by_user_id","requested_by_user_id","approved_by_user_id","approved_at","resolved_at"]
    return dict(zip(keys, row))


async def list_exemptions(tenant_id, student_id=None, status_filter=None, limit=100):
    limit = min(max(int(limit), 1), 200)
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            sql = "SELECT id,student_id,exemption_type,status,starts_at,ends_at,reason,source_type,source_id,created_by_user_id,requested_by_user_id,approved_by_user_id,approved_at,resolved_at FROM attendance_exemptions WHERE tenant_id=%s"
            params = [sid(tenant_id)]
            if student_id:
                sql += " AND student_id=%s"
                params.append(sid(student_id))
            if status_filter:
                sql += " AND status=%s"
                params.append(status_filter)
            sql += " ORDER BY starts_at DESC LIMIT %s"
            params.append(limit)
            await cur.execute(sql, params)
            rows = await cur.fetchall()
    keys = ["id","student_id","exemption_type","status","starts_at","ends_at","reason","source_type","source_id","created_by_user_id","requested_by_user_id","approved_by_user_id","approved_at","resolved_at"]
    return [dict(zip(keys, row)) for row in rows]


async def resolve_exemption(tenant_id, user_id, exemption_id, approve):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT id,student_id,exemption_type,status,starts_at,ends_at,requested_by_user_id FROM attendance_exemptions "
                    "WHERE id=%s AND tenant_id=%s FOR UPDATE",
                    (sid(exemption_id), sid(tenant_id)),
                )
                row = await cur.fetchone()
                if not row:
                    raise HTTPException(404, "Attendance exemption not found")
                if row[3] != "pending":
                    raise HTTPException(409, f"Attendance exemption is already {row[3]}")
                if sid(row[6]) == sid(user_id):
                    raise HTTPException(403, "The requester cannot approve their own exemption")
                await _require_exemption_permission(tenant_id, user_id, row[2])
                await _student_exists(cur, tenant_id, row[1], lock=True)
                resolved = now_utc()
                if approve:
                    await cur.execute(
                        "SELECT id FROM attendance_exemptions WHERE tenant_id=%s AND student_id=%s AND id<>%s "
                        "AND status='approved' AND starts_at < %s AND ends_at > %s LIMIT 1",
                        (sid(tenant_id), sid(row[1]), sid(exemption_id), row[5], row[4]),
                    )
                    if await cur.fetchone():
                        raise HTTPException(409, "The approved exemption overlaps another approved exemption")
                    await cur.execute(
                        "UPDATE attendance_exemptions SET status='approved',approved_by_user_id=%s,approved_at=%s,resolved_at=%s "
                        "WHERE id=%s AND tenant_id=%s AND status='pending'",
                        (sid(user_id), resolved, resolved, sid(exemption_id), sid(tenant_id)),
                    )
                else:
                    await cur.execute(
                        "UPDATE attendance_exemptions SET status='rejected',approved_by_user_id=%s,resolved_at=%s "
                        "WHERE id=%s AND tenant_id=%s AND status='pending'",
                        (sid(user_id), resolved, sid(exemption_id), sid(tenant_id)),
                    )
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
    return await get_exemption(tenant_id, exemption_id)


async def cancel_exemption(tenant_id, user_id, exemption_id):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT status,student_id,exemption_type FROM attendance_exemptions WHERE id=%s AND tenant_id=%s FOR UPDATE",
                    (sid(exemption_id), sid(tenant_id)),
                )
                row = await cur.fetchone()
                if not row:
                    raise HTTPException(404, "Attendance exemption not found")
                if row[0] not in ("pending", "approved"):
                    raise HTTPException(409, f"Attendance exemption is already {row[0]}")
                await _require_exemption_permission(tenant_id, user_id, row[2])
                await _student_exists(cur, tenant_id, row[1], lock=True)
                resolved = now_utc()
                await cur.execute(
                    "UPDATE attendance_exemptions SET status='cancelled',resolved_at=%s WHERE id=%s AND tenant_id=%s",
                    (resolved, sid(exemption_id), sid(tenant_id)),
                )
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
    return await get_exemption(tenant_id, exemption_id)


async def find_active_exemption(cur, tenant_id, student_id, starts_at, ends_at=None, lock=False):
    end = ends_at or starts_at
    lock_sql = " FOR UPDATE" if lock else ""
    await cur.execute(
        "SELECT id,exemption_type,status,starts_at,ends_at,reason FROM attendance_exemptions "
        "WHERE tenant_id=%s AND student_id=%s AND status='approved' "
        "AND starts_at<=%s AND ends_at>=%s "
        "ORDER BY CASE exemption_type WHEN 'sickbay' THEN 1 WHEN 'leave' THEN 2 WHEN 'suspension' THEN 3 WHEN 'official_duty' THEN 4 ELSE 5 END, starts_at DESC LIMIT 1" + lock_sql,
        (sid(tenant_id), sid(student_id), starts_at, end),
    )
    return await cur.fetchone()
