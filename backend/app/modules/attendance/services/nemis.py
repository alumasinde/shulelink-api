from datetime import date
from uuid import UUID

from app.core.database import get_pool


async def stage_daily_attendance(tenant_id: UUID, attendance_date: date, academic_year_id: UUID | None = None, academic_term_id: UUID | None = None):
    """Aggregate internal attendance into a stable staging dataset.

    This intentionally does not claim to be the official NEMIS submission format.
    An adapter/exporter can consume this staging layer once the current external
    specification is confirmed.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT ar.student_id, s.nemis_upi, "
                "SUM(CASE WHEN ast.code='present' THEN 1 ELSE 0 END), "
                "SUM(CASE WHEN ast.code='absent' THEN 1 ELSE 0 END), "
                "SUM(CASE WHEN ast.code='late' THEN 1 ELSE 0 END), "
                "SUM(CASE WHEN ast.code IN ('on_leave','excused') THEN 1 ELSE 0 END) "
                "FROM attendance_records ar "
                "JOIN attendance_sessions ses ON ses.id=ar.session_id AND ses.tenant_id=ar.tenant_id "
                "JOIN attendance_statuses ast ON ast.id=ar.attendance_status_id AND ast.tenant_id=ar.tenant_id "
                "JOIN students s ON s.id=ar.student_id AND s.tenant_id=ar.tenant_id "
                "WHERE ar.tenant_id=%s AND ses.session_date=%s "
                "AND (%s IS NULL OR ses.academic_year_id=%s) "
                "AND (%s IS NULL OR ses.academic_term_id=%s) "
                "GROUP BY ar.student_id,s.nemis_upi",
                (str(tenant_id), attendance_date,
                 str(academic_year_id) if academic_year_id else None, str(academic_year_id) if academic_year_id else None,
                 str(academic_term_id) if academic_term_id else None, str(academic_term_id) if academic_term_id else None),
            )
            rows = await cur.fetchall()
            for row in rows:
                await cur.execute(
                    "INSERT INTO attendance_nemis_staging "
                    "(id,tenant_id,academic_year_id,academic_term_id,student_id,nemis_upi,attendance_date,"
                    "present_count,absent_count,late_count,excused_count,source_version,export_status) "
                    "VALUES (UUID(),%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'internal-v1','pending') "
                    "ON DUPLICATE KEY UPDATE "
                    "present_count=VALUES(present_count),absent_count=VALUES(absent_count),"
                    "late_count=VALUES(late_count),excused_count=VALUES(excused_count),"
                    "nemis_upi=VALUES(nemis_upi),export_status='pending',validation_message=NULL",
                    (str(tenant_id), str(academic_year_id) if academic_year_id else None,
                     str(academic_term_id) if academic_term_id else None, row[0], row[1], attendance_date,
                     row[2], row[3], row[4], row[5]),
                )
    return {"date": attendance_date, "staged": len(rows)}
