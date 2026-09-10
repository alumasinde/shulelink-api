from uuid import UUID, uuid4
from fastapi import HTTPException
from app.core.database import get_pool


def sid(v): return str(v) if v is not None else None

async def _exists(cur, table, tenant_id, item_id):
    await cur.execute(f'SELECT 1 FROM {table} WHERE id=%s AND tenant_id=%s', (sid(item_id), sid(tenant_id)))
    return await cur.fetchone() is not None

async def _period_slots(cur, tenant_id, period_id, duration):
    await cur.execute('SELECT sort_order FROM timetable_periods WHERE id=%s AND tenant_id=%s AND is_active=1', (sid(period_id), sid(tenant_id)))
    start = await cur.fetchone()
    if not start: raise HTTPException(404, 'Period not found or inactive')
    await cur.execute('''SELECT id,sort_order,is_break FROM timetable_periods
        WHERE tenant_id=%s AND is_active=1 AND sort_order>=%s ORDER BY sort_order LIMIT %s''', (sid(tenant_id), start[0], duration))
    rows = await cur.fetchall()
    if len(rows) != duration or any(bool(r[2]) for r in rows):
        raise HTTPException(400, 'The lesson duration does not fit in contiguous active teaching periods')
    return [sid(r[0]) for r in rows]

async def create_timetable(tenant_id, payload):
    pool=get_pool(); item_id=uuid4(); duration=max(int(payload.get('duration_periods') or 1), 2 if payload.get('is_double') else 1)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            for table,key,label in [('academic_years','academic_year_id','Academic year'),('academic_terms','academic_term_id','Academic term'),('class_levels','class_level_id','Class level'),('subjects','subject_id','Subject'),('teachers','teacher_id','Teacher'),('timetable_periods','period_id','Period')]:
                if not await _exists(cur,table,tenant_id,payload[key]): raise HTTPException(404,f'{label} not found')
            await cur.execute('SELECT academic_year_id FROM academic_terms WHERE id=%s AND tenant_id=%s',(sid(payload['academic_term_id']),sid(tenant_id)))
            if not await cur.fetchone() or sid((await _term_year(cur, payload['academic_term_id'], tenant_id))) != sid(payload['academic_year_id']): raise HTTPException(400,'Academic term does not belong to the selected academic year')
            if payload.get('stream_id'):
                await cur.execute('SELECT class_level_id FROM streams WHERE id=%s AND tenant_id=%s',(sid(payload['stream_id']),sid(tenant_id)))
                row=await cur.fetchone()
                if not row or sid(row[0])!=sid(payload['class_level_id']): raise HTTPException(400,'Stream does not belong to the selected class level')
            await cur.execute('SELECT 1 FROM teacher_assignments WHERE tenant_id=%s AND teacher_id=%s AND academic_term_id=%s AND class_level_id=%s AND (stream_id <=> %s) AND subject_id=%s',(sid(tenant_id),sid(payload['teacher_id']),sid(payload['academic_term_id']),sid(payload['class_level_id']),sid(payload.get('stream_id')),sid(payload['subject_id'])))
            if not await cur.fetchone(): raise HTTPException(400,'Teacher is not assigned to this subject/class/stream for the selected term')
            periods=await _period_slots(cur,tenant_id,payload['period_id'],duration)
            for period_id in periods:
                await cur.execute('SELECT 1 FROM timetable_entries WHERE tenant_id=%s AND academic_term_id=%s AND class_level_id=%s AND (stream_id <=> %s) AND day_of_week=%s AND period_id=%s LIMIT 1',(sid(tenant_id),sid(payload['academic_term_id']),sid(payload['class_level_id']),sid(payload.get('stream_id')),payload['day_of_week'],period_id))
                if await cur.fetchone(): raise HTTPException(409,'Class has a timetable conflict in the selected lesson duration')
                await cur.execute('SELECT 1 FROM timetable_entries WHERE tenant_id=%s AND academic_term_id=%s AND teacher_id=%s AND day_of_week=%s AND period_id=%s LIMIT 1',(sid(tenant_id),sid(payload['academic_term_id']),sid(payload['teacher_id']),payload['day_of_week'],period_id))
                if await cur.fetchone(): raise HTTPException(409,'Teacher has a timetable conflict in the selected lesson duration')
                if payload.get('room_id'):
                    if not await _exists(cur,'timetable_rooms',tenant_id,payload['room_id']): raise HTTPException(404,'Room not found')
                    await cur.execute('SELECT 1 FROM timetable_entries WHERE tenant_id=%s AND academic_term_id=%s AND room_id=%s AND day_of_week=%s AND period_id=%s LIMIT 1',(sid(tenant_id),sid(payload['academic_term_id']),sid(payload['room_id']),payload['day_of_week'],period_id))
                    if await cur.fetchone(): raise HTTPException(409,'Room has a timetable conflict in the selected lesson duration')
            await cur.execute('''INSERT INTO timetable_entries
                (id,tenant_id,academic_year_id,academic_term_id,class_level_id,stream_id,subject_id,teacher_id,room_id,period_id,day_of_week,duration_periods,is_double,notes)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                (sid(item_id),sid(tenant_id),sid(payload['academic_year_id']),sid(payload['academic_term_id']),sid(payload['class_level_id']),sid(payload.get('stream_id')),sid(payload['subject_id']),sid(payload['teacher_id']),sid(payload.get('room_id')),sid(payload['period_id']),payload['day_of_week'],duration,duration>1,payload.get('notes')))
    return await get_timetable_entry(tenant_id,item_id)

async def _term_year(cur, term_id, tenant_id):
    await cur.execute('SELECT academic_year_id FROM academic_terms WHERE id=%s AND tenant_id=%s',(sid(term_id),sid(tenant_id)))
    row=await cur.fetchone(); return row[0] if row else None

async def get_timetable_entry(tenant_id, entry_id):
    pool=get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('''SELECT e.id,e.academic_year_id,e.academic_term_id,e.class_level_id,e.stream_id,e.subject_id,e.teacher_id,e.room_id,e.period_id,e.day_of_week,e.duration_periods,e.is_double,e.notes,CONCAT(te.first_name," ",te.last_name),cl.name,st.name,s.name,r.name,p.name
                FROM timetable_entries e JOIN teachers te ON te.id=e.teacher_id AND te.tenant_id=e.tenant_id JOIN class_levels cl ON cl.id=e.class_level_id AND cl.tenant_id=e.tenant_id LEFT JOIN streams st ON st.id=e.stream_id AND st.tenant_id=e.tenant_id JOIN subjects s ON s.id=e.subject_id AND s.tenant_id=e.tenant_id LEFT JOIN timetable_rooms r ON r.id=e.room_id AND r.tenant_id=e.tenant_id JOIN timetable_periods p ON p.id=e.period_id AND p.tenant_id=e.tenant_id
                WHERE e.id=%s AND e.tenant_id=%s''',(sid(entry_id),sid(tenant_id)))
            row=await cur.fetchone()
    if not row: raise HTTPException(404,'Timetable entry not found')
    return {'id':str(row[0]),'academic_year_id':str(row[1]),'academic_term_id':str(row[2]),'class_level_id':str(row[3]),'stream_id':str(row[4]) if row[4] else None,'subject_id':str(row[5]),'teacher_id':str(row[6]),'room_id':str(row[7]) if row[7] else None,'period_id':str(row[8]),'day_of_week':row[9],'duration_periods':int(row[10]),'is_double':bool(row[11]),'notes':row[12],'teacher_name':row[13],'class_name':row[14],'stream_name':row[15],'subject_name':row[16],'room_name':row[17],'period_name':row[18]}

async def list_timetable(tenant_id, term_id=None, class_level_id=None, stream_id=None, day_of_week=None):
    sql='''SELECT e.id,e.academic_year_id,e.academic_term_id,e.class_level_id,e.stream_id,e.subject_id,e.teacher_id,e.room_id,e.period_id,e.day_of_week,e.duration_periods,e.is_double,e.notes,CONCAT(te.first_name," ",te.last_name),cl.name,st.name,s.name,r.name,p.name FROM timetable_entries e JOIN teachers te ON te.id=e.teacher_id AND te.tenant_id=e.tenant_id JOIN class_levels cl ON cl.id=e.class_level_id AND cl.tenant_id=e.tenant_id LEFT JOIN streams st ON st.id=e.stream_id AND st.tenant_id=e.tenant_id JOIN subjects s ON s.id=e.subject_id AND s.tenant_id=e.tenant_id LEFT JOIN timetable_rooms r ON r.id=e.room_id AND r.tenant_id=e.tenant_id JOIN timetable_periods p ON p.id=e.period_id AND p.tenant_id=e.tenant_id WHERE e.tenant_id=%s'''
    args=[sid(tenant_id)]
    for col,value in [('academic_term_id',term_id),('class_level_id',class_level_id),('stream_id',stream_id),('day_of_week',day_of_week)]:
        if value is not None: sql+=f' AND e.{col}=%s'; args.append(sid(value))
    sql+=' ORDER BY e.day_of_week,p.sort_order,cl.level_order,cl.name,st.name,s.name'
    pool=get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql,args); rows=await cur.fetchall()
    return [{'id':str(r[0]),'academic_year_id':str(r[1]),'academic_term_id':str(r[2]),'class_level_id':str(r[3]),'stream_id':str(r[4]) if r[4] else None,'subject_id':str(r[5]),'teacher_id':str(r[6]),'room_id':str(r[7]) if r[7] else None,'period_id':str(r[8]),'day_of_week':r[9],'duration_periods':int(r[10]),'is_double':bool(r[11]),'notes':r[12],'teacher_name':r[13],'class_name':r[14],'stream_name':r[15],'subject_name':r[16],'room_name':r[17],'period_name':r[18]} for r in rows]

async def delete_timetable(tenant_id, entry_id):
    pool=get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('DELETE FROM timetable_entries WHERE id=%s AND tenant_id=%s',(sid(entry_id),sid(tenant_id)))
            if cur.rowcount==0: raise HTTPException(404,'Timetable entry not found')
