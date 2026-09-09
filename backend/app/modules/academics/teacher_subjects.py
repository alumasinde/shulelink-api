from uuid import UUID, uuid4
from fastapi import HTTPException
from app.core.database import get_pool

def sid(v): return str(v) if v is not None else None

async def list_teacher_subjects(tenant_id: UUID, teacher_id: UUID):
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('''SELECT ts.subject_id,s.code,s.name,s.department_id,d.name
                FROM teacher_subjects ts JOIN subjects s ON s.id=ts.subject_id AND s.tenant_id=ts.tenant_id
                LEFT JOIN departments d ON d.id=s.department_id AND d.tenant_id=s.tenant_id
                WHERE ts.tenant_id=%s AND ts.teacher_id=%s ORDER BY s.name''', (sid(tenant_id), sid(teacher_id)))
            rows = await cur.fetchall()
    return [{'id': str(r[0]), 'code': r[1], 'name': r[2], 'department_id': str(r[3]) if r[3] else None, 'department_name': r[4]} for r in rows]

async def replace_teacher_subjects(tenant_id: UUID, teacher_id: UUID, subject_ids: list[UUID]):
    subject_ids = list(dict.fromkeys(str(x) for x in subject_ids))
    if len(subject_ids) > 2:
        raise HTTPException(422, 'A teacher can select at most two subjects')
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('SELECT id,department_id FROM teachers WHERE id=%s AND tenant_id=%s', (sid(teacher_id), sid(tenant_id)))
            teacher_row = await cur.fetchone()
            if not teacher_row: raise HTTPException(404, 'Teacher not found')
            department_id = sid(teacher_row[1])
            if subject_ids and not department_id:
                raise HTTPException(400, 'Assign a department to the teacher before selecting subjects')
            if subject_ids:
                marks = ','.join(['%s'] * len(subject_ids))
                await cur.execute(f'SELECT id,department_id FROM subjects WHERE tenant_id=%s AND id IN ({marks})', [sid(tenant_id), *subject_ids])
                rows = await cur.fetchall()
                found = {sid(r[0]) for r in rows}
                if found != set(subject_ids): raise HTTPException(404, 'One or more selected subjects were not found')
                invalid = [sid(r[0]) for r in rows if sid(r[1]) != department_id]
                if invalid: raise HTTPException(400, 'Selected subjects must belong to the teacher department')
            await cur.execute('DELETE FROM teacher_subjects WHERE tenant_id=%s AND teacher_id=%s', (sid(tenant_id), sid(teacher_id)))
            for subject_id in subject_ids:
                await cur.execute('INSERT INTO teacher_subjects (id,tenant_id,teacher_id,subject_id) VALUES (%s,%s,%s,%s)', (sid(uuid4()), sid(tenant_id), sid(teacher_id), subject_id))
    return await list_teacher_subjects(tenant_id, teacher_id)

async def list_department_subjects(tenant_id: UUID, department_id: UUID):
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('SELECT id,code,name,department_id FROM subjects WHERE tenant_id=%s AND department_id=%s AND is_active=1 ORDER BY name', (sid(tenant_id), sid(department_id)))
            rows = await cur.fetchall()
    return [{'id': str(r[0]), 'code': r[1], 'name': r[2], 'department_id': str(r[3]) if r[3] else None} for r in rows]
