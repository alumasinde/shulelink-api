from uuid import UUID
from app.core.database import get_pool


async def get_parent_portal(tenant_id: UUID, tenant_user_id: UUID):
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id,first_name,last_name,phone,alternative_phone,email,address,occupation,employer,preferred_contact_method,status FROM guardians WHERE tenant_id=%s AND tenant_user_id=%s LIMIT 1", (str(tenant_id), str(tenant_user_id)))
            guardian = await cur.fetchone()
            if not guardian:
                return None
            await cur.execute("""SELECT s.id,s.admission_number,s.first_name,s.middle_name,s.last_name,s.date_of_birth,s.gender,s.photo_url,s.status,
                sg.relationship,sg.is_primary,sg.is_emergency_contact,sg.can_pick_up,
                e.enrollment_date,ay.id,ay.name,cl.id,cl.name,st.id,st.name
                FROM student_guardians sg JOIN students s ON s.id=sg.student_id AND s.tenant_id=sg.tenant_id
                LEFT JOIN student_enrollments e ON e.id=(SELECT e2.id FROM student_enrollments e2 WHERE e2.tenant_id=s.tenant_id AND e2.student_id=s.id AND e2.status='active' ORDER BY e2.enrollment_date DESC LIMIT 1)
                LEFT JOIN academic_years ay ON ay.id=e.academic_year_id LEFT JOIN class_levels cl ON cl.id=e.class_level_id LEFT JOIN streams st ON st.id=e.stream_id
                WHERE sg.tenant_id=%s AND sg.guardian_id=%s ORDER BY s.last_name,s.first_name""", (str(tenant_id), str(guardian[0])))
            children = []
            for row in await cur.fetchall():
                children.append({
                    "id": str(row[0]), "admission_number": row[1], "first_name": row[2], "middle_name": row[3], "last_name": row[4],
                    "date_of_birth": row[5], "gender": row[6], "photo_url": row[7], "status": row[8],
                    "relationship": row[9], "is_primary": bool(row[10]), "is_emergency_contact": bool(row[11]), "can_pick_up": bool(row[12]),
                    "enrollment": None if row[13] is None else {"enrollment_date": row[13], "academic_year": None if row[14] is None else {"id": str(row[14]), "name": row[15]}, "class": None if row[16] is None else {"id": str(row[16]), "name": row[17]}, "stream": None if row[18] is None else {"id": str(row[18]), "name": row[19]}},
                })
            return {"id": str(guardian[0]), "first_name": guardian[1], "last_name": guardian[2], "phone": guardian[3], "alternative_phone": guardian[4], "email": guardian[5], "address": guardian[6], "occupation": guardian[7], "employer": guardian[8], "preferred_contact_method": guardian[9], "status": guardian[10], "children": children}
