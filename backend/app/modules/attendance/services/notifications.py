from uuid import UUID, uuid4

from app.core.database import get_pool


async def queue_day_scholar_absence(tenant_id: UUID, session_id: UUID, student_id: UUID):
    """Queue an absence notification without coupling attendance to an SMS provider."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT g.phone, s.first_name, ses.session_date "
                "FROM students s "
                "JOIN student_guardians sg ON sg.student_id=s.id AND sg.tenant_id=s.tenant_id AND sg.is_primary=1 "
                "JOIN guardians g ON g.id=sg.guardian_id AND g.tenant_id=s.tenant_id "
                "JOIN attendance_sessions ses ON ses.id=%s AND ses.tenant_id=s.tenant_id "
                "WHERE s.id=%s AND s.tenant_id=%s AND s.residency_type='day_scholar' LIMIT 1",
                (str(session_id), str(student_id), str(tenant_id)),
            )
            row = await cur.fetchone()
            if not row or not row[0]:
                return None
            await cur.execute(
                "INSERT IGNORE INTO attendance_outbox "
                "(id,tenant_id,event_type,aggregate_type,aggregate_id,student_id,recipient,channel,payload_json) "
                "VALUES (%s,%s,'morning_absence','attendance_session',%s,%s,%s,'sms',JSON_OBJECT('student_name',%s,'date',%s))",
                (str(uuid4()), str(tenant_id), str(session_id), str(student_id), row[0], row[1], row[2]),
            )
            return {"queued": True, "channel": "sms"}
