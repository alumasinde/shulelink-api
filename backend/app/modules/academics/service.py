from uuid import UUID, uuid4
from fastapi import HTTPException
from app.core.database import get_pool


def _str(v): return str(v) if v is not None else None

def _dict(row, keys):
    d = dict(zip(keys, row))
    for k, v in list(d.items()):
        if k.endswith('_id') and v is not None: d[k] = str(v)
        if k in {'is_active','is_break','is_double'}: d[k] = bool(v)
    return d

async def _exists(cur, table, tenant_id, item_id):
    await cur.execute(f'SELECT 1 FROM {table} WHERE id=%s AND tenant_id=%s', (str(item_id), str(tenant_id)))
    return await cur.fetchone() is not None

async def _validate_user(cur, tenant_id, user_id):
    if user_id is None: return
    await cur.execute('SELECT 1 FROM tenant_memberships WHERE tenant_id=%s AND tenant_user_id=%s AND status=%s', (str(tenant_id), str(user_id), 'active'))
    if not await cur.fetchone(): raise HTTPException(404, 'Tenant user is not an active member of this school')

async def list_teachers(tenant_id, status=None, search=None):
    pool=get_pool()
    sql='''SELECT t.id,t.tenant_user_id,t.teacher_number,t.first_name,t.middle_name,t.last_name,t.gender,t.phone,t.email,t.department_id,t.employment_type,t.employment_date,t.status,t.notes,d.name
           FROM teachers t LEFT JOIN departments d ON d.id=t.department_id AND d.tenant_id=t.tenant_id
           WHERE t.tenant_id=%s'''; args=[str(tenant_id)]
    if status: sql += ' AND t.status=%s'; args.append(status)
    if search:
        sql += ' AND (t.teacher_number LIKE %s OR t.first_name LIKE %s OR t.middle_name LIKE %s OR t.last_name LIKE %s OR t.email LIKE %s)'; q=f'%{search}%'; args.extend([q]*5)
    sql += ' ORDER BY t.last_name,t.first_name,t.teacher_number LIMIT 200'
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql,args); rows=await cur.fetchall()
    keys=['id','tenant_user_id','teacher_number','first_name','middle_name','last_name','gender','phone','email','department_id','employment_type','employment_date','status','notes','department_name']
    return [_dict(r,keys) for r in rows]

async def get_teacher(tenant_id, teacher_id):
    items=await list_teachers(tenant_id)
    item=next((x for x in items if x['id']==str(teacher_id)),None)
    if not item: raise HTTPException(404,'Teacher not found')
    return item

async def create_teacher(tenant_id,payload):
    pool=get_pool(); tid=uuid4()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await _validate_user(cur,tenant_id,payload.get('tenant_user_id'))
            if payload.get('department_id') and not await _exists(cur,'departments',tenant_id,payload['department_id']): raise HTTPException(404,'Department not found')
            fields=['tenant_user_id','teacher_number','first_name','middle_name','last_name','gender','phone','email','department_id','employment_type','employment_date','status','notes']
            vals=[str(payload[k]) if isinstance(payload.get(k),UUID) else payload.get(k) for k in fields]
            try:
                await cur.execute('INSERT INTO teachers (id,tenant_id,'+','.join(fields)+') VALUES (%s,%s,'+','.join(['%s']*len(fields))+')',[str(tid),str(tenant_id),*vals])
            except Exception as exc:
                if getattr(exc,'args',[None])[0]==1062: raise HTTPException(409,'Teacher number or tenant user is already in use')
                raise
    return await get_teacher(tenant_id,tid)

async def update_teacher(tenant_id,teacher_id,payload):
    if not payload: return await get_teacher(tenant_id,teacher_id)
    pool=get_pool(); allowed={'tenant_user_id','teacher_number','first_name','middle_name','last_name','gender','phone','email','department_id','employment_type','employment_date','status','notes'}
    data={k:v for k,v in payload.items() if k in allowed}
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            if not await _exists(cur,'teachers',tenant_id,teacher_id): raise HTTPException(404,'Teacher not found')
            if 'tenant_user_id' in data: await _validate_user(cur,tenant_id,data['tenant_user_id'])
            if data.get('department_id') and not await _exists(cur,'departments',tenant_id,data['department_id']): raise HTTPException(404,'Department not found')
            sets=', '.join(f'{k}=%s' for k in data); vals=[str(v) if isinstance(v,UUID) else v for v in data.values()]
            try: await cur.execute(f'UPDATE teachers SET {sets} WHERE id=%s AND tenant_id=%s',[*vals,str(teacher_id),str(tenant_id)])
            except Exception as exc:
                if getattr(exc,'args',[None])[0]==1062: raise HTTPException(409,'Teacher number or tenant user is already in use')
                raise
    return await get_teacher(tenant_id,teacher_id)

async def list_assignments(tenant_id,year_id=None,term_id=None,teacher_id=None,class_level_id=None):
    pool=get_pool(); sql='''SELECT a.id,a.teacher_id,a.academic_year_id,a.academic_term_id,a.class_level_id,a.stream_id,a.subject_id,
       CONCAT(t.first_name,' ',t.last_name),cl.name,st.name,s.name,y.name,tm.name
       FROM teacher_assignments a JOIN teachers t ON t.id=a.teacher_id AND t.tenant_id=a.tenant_id
       JOIN class_levels cl ON cl.id=a.class_level_id AND cl.tenant_id=a.tenant_id
       LEFT JOIN streams st ON st.id=a.stream_id AND st.tenant_id=a.tenant_id
       JOIN subjects s ON s.id=a.subject_id AND s.tenant_id=a.tenant_id
       JOIN academic_years y ON y.id=a.academic_year_id AND y.tenant_id=a.tenant_id
       JOIN academic_terms tm ON tm.id=a.academic_term_id AND tm.tenant_id=a.tenant_id
       WHERE a.tenant_id=%s'''; args=[str(tenant_id)]
    for field,val in [('academic_year_id',year_id),('academic_term_id',term_id),('teacher_id',teacher_id),('class_level_id',class_level_id)]:
        if val: sql += f' AND a.{field}=%s'; args.append(str(val))
    sql+=' ORDER BY y.start_date,tm.term_number,cl.level_order,cl.name,st.name,s.name,t.last_name'
    async with pool.acquire() as conn:
        async with conn.cursor() as cur: await cur.execute(sql,args); rows=await cur.fetchall()
    keys=['id','teacher_id','academic_year_id','academic_term_id','class_level_id','stream_id','subject_id','teacher_name','class_name','stream_name','subject_name','academic_year_name','academic_term_name']
    return [_dict(r,keys) for r in rows]

async def create_assignment(tenant_id,payload):
    pool=get_pool(); aid=uuid4()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            checks=[('teachers',payload['teacher_id'],'Teacher'),('academic_years',payload['academic_year_id'],'Academic year'),('academic_terms',payload['academic_term_id'],'Academic term'),('class_levels',payload['class_level_id'],'Class level'),('subjects',payload['subject_id'],'Subject')]
            for table,item,label in checks:
                if not await _exists(cur,table,tenant_id,item): raise HTTPException(404,f'{label} not found')
            await cur.execute('SELECT academic_year_id FROM academic_terms WHERE id=%s AND tenant_id=%s',(str(payload['academic_term_id']),str(tenant_id))); term=await cur.fetchone()
            if not term or str(term[0])!=str(payload['academic_year_id']): raise HTTPException(400,'Academic term does not belong to the selected academic year')
            if payload.get('stream_id'):
                await cur.execute('SELECT class_level_id FROM streams WHERE id=%s AND tenant_id=%s',(str(payload['stream_id']),str(tenant_id))); stream=await cur.fetchone()
                if not stream or str(stream[0])!=str(payload['class_level_id']): raise HTTPException(400,'Stream does not belong to the selected class level')
            await cur.execute('SELECT 1 FROM class_subjects WHERE tenant_id=%s AND class_level_id=%s AND subject_id=%s',(str(tenant_id),str(payload['class_level_id']),str(payload['subject_id'])))
            if not await cur.fetchone(): raise HTTPException(400,'Subject is not assigned to this class level')
            # MySQL UNIQUE permits multiple NULL stream values, so explicitly guard the nullable natural key.
            stream_clause='a.stream_id <=> %s'
            await cur.execute(f'''SELECT 1 FROM teacher_assignments a WHERE a.tenant_id=%s AND a.teacher_id=%s AND a.academic_term_id=%s AND a.class_level_id=%s AND {stream_clause} AND a.subject_id=%s''',(str(tenant_id),str(payload['teacher_id']),str(payload['academic_term_id']),str(payload['class_level_id']),str(payload.get('stream_id')) if payload.get('stream_id') else None,str(payload['subject_id'])))
            if await cur.fetchone(): raise HTTPException(409,'This teacher assignment already exists')
            await cur.execute('''INSERT INTO teacher_assignments (id,tenant_id,teacher_id,academic_year_id,academic_term_id,class_level_id,stream_id,subject_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)''',(str(aid),str(tenant_id),str(payload['teacher_id']),str(payload['academic_year_id']),str(payload['academic_term_id']),str(payload['class_level_id']),str(payload['stream_id']) if payload.get('stream_id') else None,str(payload['subject_id'])))
    return next(x for x in await list_assignments(tenant_id) if x['id']==str(aid))

async def delete_assignment(tenant_id,assignment_id):
    pool=get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('DELETE FROM teacher_assignments WHERE id=%s AND tenant_id=%s',(str(assignment_id),str(tenant_id)))
            if cur.rowcount==0: raise HTTPException(404,'Teaching assignment not found')

async def list_rooms(tenant_id):
    pool=get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur: await cur.execute('SELECT id,code,name,capacity,room_type,is_active FROM timetable_rooms WHERE tenant_id=%s ORDER BY name,code',(str(tenant_id),)); rows=await cur.fetchall()
    return [_dict(r,['id','code','name','capacity','room_type','is_active']) for r in rows]

async def create_room(tenant_id,payload): return await _room_write(tenant_id,payload,None)
async def update_room(tenant_id,item_id,payload): return await _room_write(tenant_id,payload,item_id)

async def _room_write(tenant_id,payload,item_id):
    pool=get_pool(); fields=['code','name','capacity','room_type','is_active']; vals=[payload.get(x) for x in fields]
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                if item_id:
                    if not await _exists(cur,'timetable_rooms',tenant_id,item_id): raise HTTPException(404,'Room not found')
                    await cur.execute('UPDATE timetable_rooms SET code=%s,name=%s,capacity=%s,room_type=%s,is_active=%s WHERE id=%s AND tenant_id=%s',[*vals,str(item_id),str(tenant_id)])
                else:
                    item_id=uuid4(); await cur.execute('INSERT INTO timetable_rooms (id,tenant_id,'+','.join(fields)+') VALUES (%s,%s,'+','.join(['%s']*len(fields))+')',[str(item_id),str(tenant_id),*vals])
            except Exception as exc:
                if getattr(exc,'args',[None])[0]==1062: raise HTTPException(409,'Room code already exists')
                raise
    return next(x for x in await list_rooms(tenant_id) if x['id']==str(item_id))

async def list_periods(tenant_id):
    pool=get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur: await cur.execute('SELECT id,code,name,start_time,end_time,is_break,sort_order,is_active FROM timetable_periods WHERE tenant_id=%s ORDER BY sort_order,start_time',(str(tenant_id),)); rows=await cur.fetchall()
    return [_dict(r,['id','code','name','start_time','end_time','is_break','sort_order','is_active']) for r in rows]

async def create_period(tenant_id,payload): return await _period_write(tenant_id,payload,None)
async def update_period(tenant_id,item_id,payload): return await _period_write(tenant_id,payload,item_id)

async def _period_write(tenant_id,payload,item_id):
    if payload['end_time'] <= payload['start_time']: raise HTTPException(400,'end_time must be after start_time')
    pool=get_pool(); fields=['code','name','start_time','end_time','is_break','sort_order','is_active']; vals=[payload.get(x) for x in fields]
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                if item_id:
                    if not await _exists(cur,'timetable_periods',tenant_id,item_id): raise HTTPException(404,'Period not found')
                    await cur.execute('UPDATE timetable_periods SET '+','.join(f'{x}=%s' for x in fields)+' WHERE id=%s AND tenant_id=%s',[*vals,str(item_id),str(tenant_id)])
                else:
                    item_id=uuid4(); await cur.execute('INSERT INTO timetable_periods (id,tenant_id,'+','.join(fields)+') VALUES (%s,%s,'+','.join(['%s']*len(fields))+')',[str(item_id),str(tenant_id),*vals])
            except Exception as exc:
                if getattr(exc,'args',[None])[0]==1062: raise HTTPException(409,'Period code already exists')
                raise
    return next(x for x in await list_periods(tenant_id) if x['id']==str(item_id))

async def _validate_timetable_refs(cur,tenant_id,p):
    for table,key,label in [('academic_years','academic_year_id','Academic year'),('academic_terms','academic_term_id','Academic term'),('class_levels','class_level_id','Class level'),('subjects','subject_id','Subject'),('teachers','teacher_id','Teacher'),('timetable_periods','period_id','Period')]:
        if not await _exists(cur,table,tenant_id,p[key]): raise HTTPException(404,f'{label} not found')
    await cur.execute('SELECT academic_year_id FROM academic_terms WHERE id=%s AND tenant_id=%s',(str(p['academic_term_id']),str(tenant_id))); row=await cur.fetchone()
    if str(row[0])!=str(p['academic_year_id']): raise HTTPException(400,'Academic term does not belong to the selected academic year')
    if p.get('stream_id'):
        await cur.execute('SELECT class_level_id FROM streams WHERE id=%s AND tenant_id=%s',(str(p['stream_id']),str(tenant_id))); row=await cur.fetchone()
        if not row or str(row[0])!=str(p['class_level_id']): raise HTTPException(400,'Stream does not belong to the selected class level')
    await cur.execute('''SELECT 1 FROM teacher_assignments WHERE tenant_id=%s AND teacher_id=%s AND academic_term_id=%s AND class_level_id=%s AND (stream_id <=> %s) AND subject_id=%s''',(str(tenant_id),str(p['teacher_id']),str(p['academic_term_id']),str(p['class_level_id']),str(p.get('stream_id')) if p.get('stream_id') else None,str(p['subject_id'])))
    if not await cur.fetchone(): raise HTTPException(400,'Teacher is not assigned to this subject/class/stream for the selected term')
    if p.get('room_id') and not await _exists(cur,'timetable_rooms',tenant_id,p['room_id']): raise HTTPException(404,'Room not found')

async def _slot_conflict(cur,tenant_id,p,exclude_id=None):
    args=[str(tenant_id),str(p['academic_term_id']),str(p['class_level_id']),str(p.get('stream_id')) if p.get('stream_id') else None,p['day_of_week'],str(p['period_id']),str(p['teacher_id']),str(p.get('room_id')) if p.get('room_id') else None]
    exclude=''
    if exclude_id: exclude=' AND id<>%s'; args.append(str(exclude_id))
    await cur.execute(f'''SELECT id,teacher_id,class_level_id,stream_id,room_id FROM timetable_entries
        WHERE tenant_id=%s AND academic_term_id=%s AND ((class_level_id=%s AND stream_id <=> %s AND day_of_week=%s AND period_id=%s)
        OR (teacher_id=%s AND day_of_week=%s AND period_id=%s)
        OR (room_id IS NOT NULL AND room_id=%s AND day_of_week=%s AND period_id=%s)){exclude} LIMIT 1''',(
        args[0],args[1],args[2],args[3],args[4],args[5],args[6],args[4],args[5],args[7],args[4],args[5],*args[8:]))
    return await cur.fetchone()

async def list_timetable(tenant_id,term_id=None,class_level_id=None,stream_id=None,day_of_week=None):
    pool=get_pool(); sql='''SELECT e.id,e.academic_year_id,e.academic_term_id,e.class_level_id,e.stream_id,e.subject_id,e.teacher_id,e.room_id,e.period_id,e.day_of_week,e.is_double,e.notes,
      CONCAT(t.first_name,' ',t.last_name),cl.name,st.name,s.name,r.name,p.name
      FROM timetable_entries e JOIN teachers t ON t.id=e.teacher_id AND t.tenant_id=e.tenant_id JOIN class_levels cl ON cl.id=e.class_level_id AND cl.tenant_id=e.tenant_id
      LEFT JOIN streams st ON st.id=e.stream_id AND st.tenant_id=e.tenant_id JOIN subjects s ON s.id=e.subject_id AND s.tenant_id=e.tenant_id
      LEFT JOIN timetable_rooms r ON r.id=e.room_id AND r.tenant_id=e.tenant_id JOIN timetable_periods p ON p.id=e.period_id AND p.tenant_id=e.tenant_id WHERE e.tenant_id=%s'''; args=[str(tenant_id)]
    for col,val in [('academic_term_id',term_id),('class_level_id',class_level_id),('stream_id',stream_id),('day_of_week',day_of_week)]:
        if val is not None: sql += f' AND e.{col}=%s'; args.append(str(val))
    sql+=' ORDER BY e.day_of_week,p.sort_order,p.start_time,cl.level_order,cl.name,st.name'
    async with pool.acquire() as conn:
        async with conn.cursor() as cur: await cur.execute(sql,args); rows=await cur.fetchall()
    keys=['id','academic_year_id','academic_term_id','class_level_id','stream_id','subject_id','teacher_id','room_id','period_id','day_of_week','is_double','notes','teacher_name','class_name','stream_name','subject_name','room_name','period_name']
    return [_dict(r,keys) for r in rows]

async def create_timetable(tenant_id,p):
    pool=get_pool(); eid=uuid4()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await _validate_timetable_refs(cur,tenant_id,p)
            conflict=await _slot_conflict(cur,tenant_id,p)
            if conflict: raise HTTPException(409,'Timetable conflict: class, teacher, or room is already occupied in this period')
            try:
                await cur.execute('''INSERT INTO timetable_entries (id,tenant_id,academic_year_id,academic_term_id,class_level_id,stream_id,subject_id,teacher_id,room_id,period_id,day_of_week,is_double,notes) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',(str(eid),str(tenant_id),str(p['academic_year_id']),str(p['academic_term_id']),str(p['class_level_id']),str(p['stream_id']) if p.get('stream_id') else None,str(p['subject_id']),str(p['teacher_id']),str(p['room_id']) if p.get('room_id') else None,str(p['period_id']),p['day_of_week'],p.get('is_double',False),p.get('notes')))
            except Exception as exc:
                if getattr(exc,'args',[None])[0]==1062: raise HTTPException(409,'Timetable slot conflict')
                raise
    return next(x for x in await list_timetable(tenant_id) if x['id']==str(eid))

async def delete_timetable(tenant_id,entry_id):
    pool=get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('DELETE FROM timetable_entries WHERE id=%s AND tenant_id=%s',(str(entry_id),str(tenant_id)))
            if cur.rowcount==0: raise HTTPException(404,'Timetable entry not found')

async def generate_timetable(tenant_id,req):
    pool=get_pool(); created=0; skipped=0; conflicts=[]
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            if req.get('replace_existing'):
                params=[str(tenant_id),str(req['academic_term_id'])]
                sql='DELETE FROM timetable_entries WHERE tenant_id=%s AND academic_term_id=%s'
                if req.get('class_level_id'): sql+=' AND class_level_id=%s'; params.append(str(req['class_level_id']))
                if req.get('stream_id'): sql+=' AND stream_id=%s'; params.append(str(req['stream_id']))
                await cur.execute(sql,params)
            await cur.execute('''SELECT id,teacher_id,academic_year_id,academic_term_id,class_level_id,stream_id,subject_id FROM teacher_assignments WHERE tenant_id=%s AND academic_year_id=%s AND academic_term_id=%s'''+(' AND class_level_id=%s' if req.get('class_level_id') else '')+(' AND stream_id=%s' if req.get('stream_id') else '')+' ORDER BY class_level_id,stream_id,subject_id,teacher_id',(str(tenant_id),str(req['academic_year_id']),str(req['academic_term_id']),*([str(req['class_level_id'])] if req.get('class_level_id') else []),*([str(req['stream_id'])] if req.get('stream_id') else [])))
            assignments=await cur.fetchall()
            await cur.execute('SELECT id FROM timetable_periods WHERE tenant_id=%s AND is_active=1 AND is_break=0 ORDER BY sort_order,start_time',(str(tenant_id),)); periods=[r[0] for r in await cur.fetchall()]
            if not periods: raise HTTPException(400,'No active teaching periods are configured')
            days=range(1,6)
            for a in assignments:
                lessons=min(max(int(req.get('lessons_per_week',3)),1),10)
                placed=0
                for day in days:
                    for period in periods:
                        if placed>=lessons: break
                        p={'academic_year_id':a[2],'academic_term_id':a[3],'class_level_id':a[4],'stream_id':a[5],'subject_id':a[6],'teacher_id':a[1],'room_id':None,'period_id':period,'day_of_week':day,'is_double':False,'notes':None}
                        conflict=await _slot_conflict(cur,tenant_id,p)
                        if conflict: continue
                        try:
                            await cur.execute('INSERT INTO timetable_entries (id,tenant_id,academic_year_id,academic_term_id,class_level_id,stream_id,subject_id,teacher_id,room_id,period_id,day_of_week,is_double) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',(str(uuid4()),str(tenant_id),*map(str,[a[2],a[3],a[4]]),str(a[5]) if a[5] else None,str(a[6]),str(a[1]),None,str(period),day,False))
                            created+=1; placed+=1
                        except Exception as exc:
                            if getattr(exc,'args',[None])[0]==1062: continue
                            raise
                    if placed>=lessons: break
                if placed<lessons:
                    skipped+=lessons-placed; conflicts.append(f'Could not place all requested lessons for teacher {a[1]} / subject {a[6]} / class {a[4]}')
    return {'created':created,'skipped':skipped,'conflicts':conflicts}
