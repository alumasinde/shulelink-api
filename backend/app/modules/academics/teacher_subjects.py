from uuid import UUID, uuid4
from fastapi import HTTPException
from app.core.database import get_pool, get_central_pool


def sid(v): return str(v) if v is not None else None


async def list_teacher_subjects(tenant_id: UUID, teacher_id: UUID):
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('''SELECT ts.subject_id,s.code,s.name,s.department_id,d.name
                FROM teacher_subjects ts
                JOIN subjects s ON s.id=ts.subject_id AND s.tenant_id=ts.tenant_id
                LEFT JOIN departments d ON d.id=s.department_id AND d.tenant_id=s.tenant_id
                WHERE ts.tenant_id=%s AND ts.teacher_id=%s ORDER BY s.name''', (sid(tenant_id), sid(teacher_id)))
            rows = await cur.fetchall()
    return [{'id': str(r[0]), 'code': r[1], 'name': r[2], 'department_id': str(r[3]) if r[3] else None, 'department_name': r[4]} for r in rows]


async def _get_setting(key, default=None):
    pool = get_central_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('SELECT setting_value,value_type FROM platform_academic_settings WHERE setting_key=%s AND is_active=1', (key,))
            row = await cur.fetchone()
    if not row:
        return default
    value, value_type = row
    if value_type == 'integer':
        try: return int(value)
        except (TypeError, ValueError): return default
    if value_type == 'boolean': return str(value).lower() in {'1','true','yes','on'}
    if value_type == 'json':
        import json
        try: return json.loads(value)
        except (TypeError, ValueError): return default
    if value == 'null': return None
    return value


async def replace_teacher_subjects(tenant_id: UUID, teacher_id: UUID, subject_ids: list[UUID]):
    subject_ids = list(dict.fromkeys(str(x) for x in subject_ids))
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('SELECT id,department_id FROM teachers WHERE id=%s AND tenant_id=%s', (sid(teacher_id), sid(tenant_id)))
            teacher_row = await cur.fetchone()
            if not teacher_row:
                raise HTTPException(404, 'Teacher not found')

            max_subjects = await _get_setting('academic.default_teacher_subject_limit', None)
            if max_subjects is not None and len(subject_ids) > max_subjects:
                raise HTTPException(422, f'This school allows a teacher to have at most {max_subjects} subject eligibilities')

            if subject_ids:
                marks = ','.join(['%s'] * len(subject_ids))
                await cur.execute(f'SELECT id FROM subjects WHERE tenant_id=%s AND is_active=1 AND id IN ({marks})', [sid(tenant_id), *subject_ids])
                found = {sid(r[0]) for r in await cur.fetchall()}
                if found != set(subject_ids):
                    raise HTTPException(404, 'One or more selected subjects were not found or are inactive')

                enforce_department = await _get_setting('academic.enforce_department_subject_matching', False)
                if enforce_department and teacher_row[1] is not None:
                    await cur.execute(f'SELECT id FROM subjects WHERE tenant_id=%s AND department_id=%s AND is_active=1 AND id IN ({marks})', [sid(tenant_id), sid(teacher_row[1]), *subject_ids])
                    valid = {sid(r[0]) for r in await cur.fetchall()}
                    if valid != set(subject_ids):
                        raise HTTPException(400, 'One or more selected subjects are outside the configured teacher department rule')

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
