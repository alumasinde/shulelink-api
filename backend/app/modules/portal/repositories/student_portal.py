from uuid import UUID
from app.core.database import get_pool


async def get_student_portal(tenant_id: UUID, tenant_user_id: UUID):
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""SELECT s.id,s.admission_number,s.first_name,s.middle_name,s.last_name,s.date_of_birth,s.gender,s.nationality,s.admission_date,s.photo_url,s.status,
                e.id,e.enrollment_date,e.status,ay.id,ay.name,cl.id,cl.name,st.id,st.name
                FROM students s
                LEFT JOIN student_enrollments e ON e.id=(SELECT e2.id FROM student_enrollments e2 WHERE e2.tenant_id=s.tenant_id AND e2.student_id=s.id AND e2.status='active' ORDER BY e2.enrollment_date DESC LIMIT 1)
                LEFT JOIN academic_years ay ON ay.id=e.academic_year_id
                LEFT JOIN class_levels cl ON cl.id=e.class_level_id
                LEFT JOIN streams st ON st.id=e.stream_id
                WHERE s.tenant_id=%s AND s.tenant_user_id=%s LIMIT 1""", (str(tenant_id), str(tenant_user_id)))
            row = await cur.fetchone()
            if not row:
                return None
            return {
                "id": str(row[0]), "admission_number": row[1], "first_name": row[2], "middle_name": row[3], "last_name": row[4],
                "date_of_birth": row[5], "gender": row[6], "nationality": row[7], "admission_date": row[8], "photo_url": row[9], "status": row[10],
                "enrollment": None if row[11] is None else {
                    "id": str(row[11]), "enrollment_date": row[12], "status": row[13],
                    "academic_year": None if row[14] is None else {"id": str(row[14]), "name": row[15]},
                    "class": None if row[16] is None else {"id": str(row[16]), "name": row[17]},
                    "stream": None if row[18] is None else {"id": str(row[18]), "name": row[19]},
                },
            }
