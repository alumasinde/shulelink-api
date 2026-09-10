from datetime import datetime, time

from app.core.database import get_pool
from app.modules.attendance.services.exemptions import find_active_exemption

EXEMPTION_STATUS = {
    "leave": "on_leave",
    "sickbay": "excused",
    "suspension": "on_leave",
    "official_duty": "excused",
    "approved_absence": "excused",
}


def sid(value):
    return str(value) if value is not None else None


def session_window(session_date, starts_at, ends_at):
    start = starts_at or datetime.combine(session_date, time.min)
    end = ends_at or datetime.combine(session_date, time.max)
    return start, end


async def apply_approved_exemptions(tenant_id, session_id, payload):
    """Apply exemptions using the exact full-session boundary enforced by SQL."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT session_date,scheduled_start_at,scheduled_end_at "
                "FROM attendance_sessions WHERE id=%s AND tenant_id=%s LIMIT 1",
                (sid(session_id), sid(tenant_id)),
            )
            session = await cur.fetchone()
            if not session:
                return payload
            start, end = session_window(session[0], session[1], session[2])
            for item in payload.items:
                exemption = await find_active_exemption(
                    cur, tenant_id, item.student_id, start, end
                )
                if exemption:
                    item.status_code = EXEMPTION_STATUS.get(exemption[1], "excused")
                    item.remarks = item.remarks or exemption[5]
    return payload
