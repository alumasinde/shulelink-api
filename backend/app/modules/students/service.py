from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4
from fastapi import HTTPException
from app.core.database import get_pool
from app.modules.students.admission import next_admission_number

STUDENT_COLUMNS = "id,tenant_id,admission_number,first_name,middle_name,last_name,date_of_birth,gender,nationality,birth_certificate_number,admission_date,previous_school,photo_url,status,medical_notes,emergency_notes"
STUDENT_SELECT = STUDENT_COLUMNS + ", (SELECT cl.name FROM student_enrollments e JOIN class_levels cl ON cl.id=e.class_level_id WHERE e.student_id=students.id AND e.tenant_id=students.tenant_id AND e.status='active' ORDER BY e.enrollment_date DESC LIMIT 1) AS current_class_name, (SELECT s.name FROM student_enrollments e JOIN streams s ON s.id=e.stream_id WHERE e.student_id=students.id AND e.tenant_id=students.tenant_id AND e.status='active' AND e.stream_id IS NOT NULL ORDER BY e.enrollment_date DESC LIMIT 1) AS current_stream_name"
STUDENT_KEYS = STUDENT_COLUMNS.split(",") + ["current_class_name", "current_stream_name"]
GUARDIAN_COLUMNS = "id,tenant_id,first_name,last_name,phone,alternative_phone,email,address,occupation,employer,preferred_contact_method,status"


def _str(value):
    return str(value) if value is not None else None


def _bool(value):
    return bool(value)


def _student(row):
    d = dict(zip(STUDENT_KEYS, row))
    for key in ("id", "tenant_id"):
        d[key] = _str(d[key])
    d["is_active"] = d["status"] == "active"
    return d


def _guardian(row):
    keys = GUARDIAN_COLUMNS.split(",")
    d = dict(zip(keys, row))
    d["id"] = _str(d["id"])
    d["tenant_id"] = _str(d["tenant_id"])
    return d


async def _one(query, args=()):
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, args)
            return await cur.fetchone()


async def list_students(tenant_id: UUID, search: str | None = None, status: str | None = None, limit: int = 50, offset: int = 0):
    pool = get_pool()
    where = ["students.tenant_id=%s"]
    args = [str(tenant_id)]
    if search:
        where.append("(students.admission_number LIKE %s OR students.first_name LIKE %s OR students.middle_name LIKE %s OR students.last_name LIKE %s)")
        term = f"%{search.strip()}%"
        args.extend([term] * 4)
    if status:
        where.append("students.status=%s")
        args.append(status)
    args.extend([limit, offset])
    sql = f"SELECT {STUDENT_SELECT} FROM students WHERE {' AND '.join(where)} ORDER BY students.last_name,students.first_name,students.admission_number LIMIT %s OFFSET %s"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, args)
            rows = await cur.fetchall()
    return [_student(r) for r in rows]


async def count_students(tenant_id: UUID):
    row = await _one("SELECT COUNT(*) FROM students WHERE tenant_id=%s", (str(tenant_id),))
    return int(row[0]) if row else 0


async def create_student(tenant_id: UUID, data: dict):
    item_id = uuid4()
    admission_date = data.get("admission_date")
    admission_number = await next_admission_number(tenant_id, admission_date)
    fields = ["admission_number","first_name","middle_name","last_name","date_of_birth","gender","nationality","birth_certificate_number","admission_date","previous_school","photo_url","status","medical_notes","emergency_notes"]
    values = [str(item_id), str(tenant_id), admission_number] + [data.get(f) for f in fields[1:]]
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(f"INSERT INTO students (id,tenant_id,{','.join(fields)}) VALUES ({','.join(['%s']*(2+len(fields)))})", values)
    except Exception as exc:
        if getattr(exc, "args", [None])[0] == 1062:
            raise HTTPException(409, "Admission number already exists in this school")
        raise
    return await get_student(tenant_id, item_id)


async def get_student(tenant_id: UUID, student_id: UUID):
    row = await _one(f"SELECT {STUDENT_SELECT} FROM students WHERE students.id=%s AND students.tenant_id=%s", (str(student_id), str(tenant_id)))
    if not row:
        raise HTTPException(404, "Student not found")
    return _student(row)


async def update_student(tenant_id: UUID, student_id: UUID, data: dict):
    data = {k: v for k, v in data.items() if v is not None}
    if not data:
        return await get_student(tenant_id, student_id)
    allowed = {"first_name","middle_name","last_name","date_of_birth","gender","nationality","birth_certificate_number","admission_date","previous_school","photo_url","status","medical_notes","emergency_notes"}
    data = {k: v for k, v in data.items() if k in allowed}
    if not data:
        return await get_student(tenant_id, student_id)
    assignments = ",".join(f"{k}=%s" for k in data)
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(f"UPDATE students SET {assignments} WHERE id=%s AND tenant_id=%s", [*data.values(), str(student_id), str(tenant_id)])
                if cur.rowcount == 0:
                    raise HTTPException(404, "Student not found")
    except HTTPException:
        raise
    return await get_student(tenant_id, student_id)


async def set_student_photo(tenant_id: UUID, student_id: UUID, photo_url: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("UPDATE students SET photo_url=%s WHERE id=%s AND tenant_id=%s", (photo_url, str(student_id), str(tenant_id)))
            if cur.rowcount == 0:
                raise HTTPException(404, "Student not found")
    return await get_student(tenant_id, student_id)


async def list_guardians(tenant_id: UUID, search: str | None = None, limit: int = 50, offset: int = 0):
    pool = get_pool()
    where = ["tenant_id=%s"]
    args = [str(tenant_id)]
    if search:
        where.append("(first_name LIKE %s OR last_name LIKE %s OR phone LIKE %s OR email LIKE %s)")
        term = f"%{search.strip()}%"
        args.extend([term] * 4)
    args.extend([limit, offset])
    sql = f"SELECT {GUARDIAN_COLUMNS} FROM guardians WHERE {' AND '.join(where)} ORDER BY last_name,first_name LIMIT %s OFFSET %s"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, args)
            rows = await cur.fetchall()
    return [_guardian(r) for r in rows]


async def create_guardian(tenant_id: UUID, data: dict):
    item_id = uuid4()
    fields = ["first_name","last_name","phone","alternative_phone","email","address","occupation","employer","preferred_contact_method","status"]
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"INSERT INTO guardians (id,tenant_id,{','.join(fields)}) VALUES ({','.join(['%s']*(2+len(fields)))})", [str(item_id),str(tenant_id)]+[data.get(f) for f in fields])
    row = await _one(f"SELECT {GUARDIAN_COLUMNS} FROM guardians WHERE id=%s AND tenant_id=%s", (str(item_id),str(tenant_id)))
    return _guardian(row)


async def get_guardian(tenant_id: UUID, guardian_id: UUID):
    row = await _one(f"SELECT {GUARDIAN_COLUMNS} FROM guardians WHERE id=%s AND tenant_id=%s", (str(guardian_id),str(tenant_id)))
    if not row:
        raise HTTPException(404, "Guardian not found")
    return _guardian(row)


async def update_guardian(tenant_id: UUID, guardian_id: UUID, data: dict):
    data = {k: v for k,v in data.items() if k in {"first_name","last_name","phone","alternative_phone","email","address","occupation","employer","preferred_contact_method","status"}}
    if not data:
        return await get_guardian(tenant_id, guardian_id)
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"UPDATE guardians SET {','.join(f'{k}=%s' for k in data)} WHERE id=%s AND tenant_id=%s", [*data.values(),str(guardian_id),str(tenant_id)])
            if cur.rowcount == 0:
                raise HTTPException(404,"Guardian not found")
    return await get_guardian(tenant_id, guardian_id)


async def list_student_guardians(tenant_id: UUID, student_id: UUID):
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""SELECT sg.id,sg.student_id,sg.guardian_id,sg.relationship,sg.is_primary,sg.is_emergency_contact,sg.can_pick_up,
            g.id,g.tenant_id,g.first_name,g.last_name,g.phone,g.alternative_phone,g.email,g.address,g.occupation,g.employer,g.preferred_contact_method,g.status
            FROM student_guardians sg JOIN guardians g ON g.id=sg.guardian_id
            WHERE sg.tenant_id=%s AND sg.student_id=%s ORDER BY sg.is_primary DESC,g.last_name,g.first_name""", (str(tenant_id),str(student_id)))
            rows=await cur.fetchall()
    if not rows and not await _student_exists(tenant_id, student_id):
        raise HTTPException(404,"Student not found")
    result=[]
    for r in rows:
        result.append({"id":str(r[0]),"student_id":str(r[1]),"guardian_id":str(r[2]),"relationship":r[3],"is_primary":_bool(r[4]),"is_emergency_contact":_bool(r[5]),"can_pick_up":_bool(r[6]),"guardian":_guardian(r[7:])})
    return result


async def _student_exists(tenant_id, student_id):
    return bool(await _one("SELECT 1 FROM students WHERE id=%s AND tenant_id=%s",(str(student_id),str(tenant_id))))


async def add_student_guardian(tenant_id: UUID, student_id: UUID, data: dict):
    if not await _student_exists(tenant_id, student_id):
        raise HTTPException(404,"Student not found")
    if not await _one("SELECT id FROM guardians WHERE id=%s AND tenant_id=%s",(str(data['guardian_id']),str(tenant_id))):
        raise HTTPException(404,"Guardian not found")
    pool=get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                if data.get("is_primary"):
                    await cur.execute("UPDATE student_guardians SET is_primary=0 WHERE tenant_id=%s AND student_id=%s",(str(tenant_id),str(student_id)))
                await cur.execute("INSERT INTO student_guardians (id,tenant_id,student_id,guardian_id,relationship,is_primary,is_emergency_contact,can_pick_up) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",(str(uuid4()),str(tenant_id),str(student_id),str(data['guardian_id']),data['relationship'],data.get('is_primary',False),data.get('is_emergency_contact',False),data.get('can_pick_up',True)))
            except Exception as exc:
                if getattr(exc,'args',[None])[0]==1062: raise HTTPException(409,"Guardian is already linked to this student")
                raise
    return (await list_student_guardians(tenant_id,student_id))[-1]


async def remove_student_guardian(tenant_id: UUID, student_id: UUID, guardian_id: UUID):
    pool=get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM student_guardians WHERE tenant_id=%s AND student_id=%s AND guardian_id=%s",(str(tenant_id),str(student_id),str(guardian_id)))
            if cur.rowcount==0: raise HTTPException(404,"Student-guardian relationship not found")


async def list_enrollments(tenant_id: UUID, student_id: UUID):
    pool=get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""SELECT e.id,e.student_id,e.academic_year_id,e.class_level_id,e.stream_id,e.enrollment_date,e.exit_date,e.status,e.notes,ay.name,cl.name,s.name
            FROM student_enrollments e JOIN academic_years ay ON ay.id=e.academic_year_id JOIN class_levels cl ON cl.id=e.class_level_id LEFT JOIN streams s ON s.id=e.stream_id
            WHERE e.tenant_id=%s AND e.student_id=%s ORDER BY e.enrollment_date DESC""",(str(tenant_id),str(student_id)))
            rows=await cur.fetchall()
    if not rows and not await _student_exists(tenant_id,student_id): raise HTTPException(404,"Student not found")
    return [{"id":str(r[0]),"student_id":str(r[1]),"academic_year_id":str(r[2]),"class_level_id":str(r[3]),"stream_id":_str(r[4]),"enrollment_date":r[5],"exit_date":r[6],"status":r[7],"notes":r[8],"academic_year_name":r[9],"class_name":r[10],"stream_name":r[11]} for r in rows]


async def create_enrollment(tenant_id: UUID, student_id: UUID, data: dict):
    if not await _student_exists(tenant_id,student_id): raise HTTPException(404,"Student not found")
    pool=get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1 FROM academic_years WHERE id=%s AND tenant_id=%s",(str(data['academic_year_id']),str(tenant_id)))
            if not await cur.fetchone(): raise HTTPException(404,"Academic year not found")
            await cur.execute("SELECT 1 FROM class_levels WHERE id=%s AND tenant_id=%s",(str(data['class_level_id']),str(tenant_id)))
            if not await cur.fetchone(): raise HTTPException(404,"Class level not found")
            if data.get('stream_id'):
                await cur.execute("SELECT 1 FROM streams WHERE id=%s AND class_level_id=%s AND tenant_id=%s",(str(data['stream_id']),str(data['class_level_id']),str(tenant_id)))
                if not await cur.fetchone(): raise HTTPException(404,"Stream not found for selected class")
            try:
                await cur.execute("INSERT INTO student_enrollments (id,tenant_id,student_id,academic_year_id,class_level_id,stream_id,enrollment_date,exit_date,status,notes) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(str(uuid4()),str(tenant_id),str(student_id),str(data['academic_year_id']),str(data['class_level_id']),str(data['stream_id']) if data.get('stream_id') else None,data['enrollment_date'],data.get('exit_date'),data.get('status','active'),data.get('notes')))
            except Exception as exc:
                if getattr(exc,'args',[None])[0]==1062: raise HTTPException(409,"Student is already enrolled for this academic year")
                raise
    return (await list_enrollments(tenant_id,student_id))[0]


async def update_enrollment(tenant_id: UUID, student_id: UUID, enrollment_id: UUID, data: dict):
    current=await _one("SELECT enrollment_date FROM student_enrollments WHERE id=%s AND tenant_id=%s AND student_id=%s",(str(enrollment_id),str(tenant_id),str(student_id)))
    if not current: raise HTTPException(404,"Enrollment not found")
    data={k:v for k,v in data.items() if v is not None}
    if 'stream_id' in data:
        row=await _one("SELECT e.class_level_id FROM student_enrollments e WHERE e.id=%s AND e.tenant_id=%s",(str(enrollment_id),str(tenant_id)))
        if data['stream_id'] and not await _one("SELECT 1 FROM streams WHERE id=%s AND class_level_id=%s AND tenant_id=%s",(str(data['stream_id']),str(row[0]),str(tenant_id))): raise HTTPException(404,"Stream not found for this class")
    if not data: return (await list_enrollments(tenant_id,student_id))[0]
    pool=get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"UPDATE student_enrollments SET {','.join(f'{k}=%s' for k in data)} WHERE id=%s AND tenant_id=%s AND student_id=%s",[*data.values(),str(enrollment_id),str(tenant_id),str(student_id)])
    items=await list_enrollments(tenant_id,student_id)
    return next(x for x in items if x['id']==str(enrollment_id))


async def list_document_types(tenant_id: UUID):
    rows=[]
    pool=get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id,code,name,is_required,is_active FROM student_document_types WHERE tenant_id=%s ORDER BY name",(str(tenant_id),)); rows=await cur.fetchall()
    return [{"id":str(r[0]),"code":r[1],"name":r[2],"is_required":bool(r[3]),"is_active":bool(r[4])} for r in rows]


async def create_document_type(tenant_id: UUID, data: dict):
    pool=get_pool(); item_id=uuid4()
    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("INSERT INTO student_document_types (id,tenant_id,code,name,is_required,is_active) VALUES (%s,%s,%s,%s,%s,%s)",(str(item_id),str(tenant_id),data['code'].strip(),data['name'].strip(),data.get('is_required',False),data.get('is_active',True)))
    except Exception as exc:
        if getattr(exc,'args',[None])[0]==1062: raise HTTPException(409,"Document type code or name already exists")
        raise
    return (await list_document_types(tenant_id))[-1]


async def list_documents(tenant_id: UUID, student_id: UUID):
    pool=get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""SELECT d.id,d.student_id,d.document_type_id,d.file_name,d.file_url,d.mime_type,d.file_size,d.document_number,d.issued_at,d.expires_at,d.notes,d.uploaded_by,t.name
            FROM student_documents d JOIN student_document_types t ON t.id=d.document_type_id WHERE d.tenant_id=%s AND d.student_id=%s ORDER BY d.created_at DESC""",(str(tenant_id),str(student_id))); rows=await cur.fetchall()
    if not rows and not await _student_exists(tenant_id,student_id): raise HTTPException(404,"Student not found")
    return [{"id":str(r[0]),"student_id":str(r[1]),"document_type_id":str(r[2]),"file_name":r[3],"file_url":r[4],"mime_type":r[5],"file_size":r[6],"document_number":r[7],"issued_at":r[8],"expires_at":r[9],"notes":r[10],"uploaded_by":_str(r[11]),"document_type_name":r[12]} for r in rows]


async def create_document(tenant_id: UUID, student_id: UUID, data: dict, uploaded_by: UUID):
    if not await _student_exists(tenant_id,student_id): raise HTTPException(404,"Student not found")
    if not await _one("SELECT id FROM student_document_types WHERE id=%s AND tenant_id=%s AND is_active=1",(str(data['document_type_id']),str(tenant_id))): raise HTTPException(404,"Document type not found")
    pool=get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("INSERT INTO student_documents (id,tenant_id,student_id,document_type_id,file_name,file_url,mime_type,file_size,document_number,issued_at,expires_at,notes,uploaded_by) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(str(uuid4()),str(tenant_id),str(student_id),str(data['document_type_id']),data['file_name'],data['file_url'],data.get('mime_type'),data.get('file_size'),data.get('document_number'),data.get('issued_at'),data.get('expires_at'),data.get('notes'),str(uploaded_by)))
    return (await list_documents(tenant_id,student_id))[0]
