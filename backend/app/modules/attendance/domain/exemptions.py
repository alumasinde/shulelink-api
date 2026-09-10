from datetime import datetime
from uuid import UUID


EXEMPTION_STATUS = "approved"


async def find_active_exemption(cur, tenant_id: UUID, student_id: UUID, at: datetime):
    """Return the highest-priority approved exemption covering a point in time."""
    await cur.execute(
        "SELECT id, exemption_type, source_type, source_id "
        "FROM attendance_exemptions "
        "WHERE tenant_id=%s AND student_id=%s AND status=%s "
        "AND starts_at<=%s AND ends_at>%s "
        "ORDER BY CASE exemption_type "
        "WHEN 'sickbay' THEN 1 WHEN 'leave' THEN 2 WHEN 'suspension' THEN 3 "
        "WHEN 'official_duty' THEN 4 ELSE 5 END, starts_at DESC LIMIT 1",
        (str(tenant_id), str(student_id), EXEMPTION_STATUS, at, at),
    )
    return await cur.fetchone()


async def is_exempt(cur, tenant_id: UUID, student_id: UUID, at: datetime) -> bool:
    return await find_active_exemption(cur, tenant_id, student_id, at) is not None
