from uuid import UUID, uuid4
from fastapi import HTTPException
from app.core.database import get_pool

def sid(v): return str(v) if v is not None else None

def rowdict(row, keys):
    d=dict(zip(keys,row))
    for k,v in list(d.items()):
        if k.endswith('_id') and v is not None:d[k]=str(v)
        if k in {'is_active','is_break','is_double'}:d[k]=bool(v)
    return d
async def exists(cur,table,tenant_id,item_id):
    await cur.execute(f'SELECT 1 FROM {table} WHERE id=%s AND tenant_id=%s',(sid(item_id),sid(tenant_id)));return await cur.fetchone() is not None
async def validate_user(cur,t,user_id):
    if user_id is None:return
    await cur.execute('SELECT 1 FROM tenant_memberships WHERE tenant_id=%s AND tenant_user_id=%s AND status="active"',(sid(t),sid(user_id)))
    if not await cur.fetchone():raise HTTPException(404,'Tenant user is not an active member of this school')
async def list_teachers(t,status=None,search=None):
    sql='SELECT t.id,t.tenant_user_id,t.teacher_number,t.first_name,t.middle_name,t.last_name,t.gender,t.phone,t.email,t.department_id,t.employment_type,t.employment_date,t.status,t.notes,d.name FROM teachers t LEFT JOIN departments d ON d.id=t.department_id AND d.tenant_id=t.tenant_id WHERE t.tenant_id=%s';args=[sid(t)]
    if status:sql+=' AND t.status=%s';args.append(status)
    if search:sql+=' AND (t.teacher_number LIKE %s OR t.first_name LIKE %s OR t.middle_name LIKE %s OR t.last_name LIKE %s OR t.email LIKE %s)';args += [f'%{search}%']*5
    sql+=' ORDER BY t.last_name,t.first_name,t.teacher_number LIMIT 200';pool=get_pool()
    async with pool.acquire() as c:
        async with c.cursor() as cur:await cur.execute(sql,args);rows=await cur.fetchall()
    return [rowdict(r,['id','tenant_user_id','teacher_number','first_name','middle_name','last_name','gender','phone','email','department_id','employment_type','employment_date','status','notes','department_name']) for r in rows]
async def get_teacher(t,i):
    x=next((x for x in await list_teachers(t) if x['id']==sid(i)),None)
    if not x:raise HTTPException(404,'Teacher not found')
    return x
async def create_teacher(t,p):
    pool=get_pool();i=uuid4();f=['tenant_user_id','teacher_number','first_name','middle_name','last_name','gender','phone','email','department_id','employment_type','employment_date','status','notes']
    async with pool.acquire() as c:
        async with c.cursor() as cur:
            await validate_user(cur,t,p.get('tenant_user_id'))
            if p.get('department_id') and not await exists(cur,'departments',t,p['department_id']):raise HTTPException(404,'Department not found')
            try:await cur.execute(f'INSERT INTO teachers (id,tenant_id,{",".join(f)}) VALUES (%s,%s,{",".join(["%s"]*len(f))})',[sid(i),sid(t),*[sid(p.get(k)) if isinstance(p.get(k),UUID) else p.get(k) for k in f]])
            except Exception as e:
                if getattr(e,'args',[None])[0]==1062:raise HTTPException(409,'Teacher number or tenant user is already in use')
                raise
    return await get_teacher(t,i)
async def update_teacher(t,i,p):
    if not p:return await get_teacher(t,i)
    pool=get_pool();allowed={'tenant_user_id','teacher_number','first_name','middle_name','last_name','gender','phone','email','department_id','employment_type','employment_date','status','notes'};d={k:v for k,v in p.items() if k in allowed}
    async with pool.acquire() as c:
        async with c.cursor() as cur:
            if not await exists(cur,'teachers',t,i):raise HTTPException(404,'Teacher not found')
            if 'tenant_user_id' in d:await validate_user(cur,t,d['tenant_user_id'])
            if d.get('department_id') and not await exists(cur,'departments',t,d['department_id']):raise HTTPException(404,'Department not found')
            try:await cur.execute('UPDATE teachers SET '+','.join(f'{k}=%s' for k in d)+' WHERE id=%s AND tenant_id=%s',[*[sid(v) if isinstance(v,UUID) else v for v in d.values()],sid(i),sid(t)])
            except Exception as e:
                if getattr(e,'args',[None])[0]==1062:raise HTTPException(409,'Teacher number or tenant user is already in use')
                raise
    return await get_teacher(t,i)
async def list_assignments(t,year_id=None,term_id=None,teacher_id=None,class_level_id=None):
    sql='SELECT a.id,a.teacher_id,a.academic_year_id,a.academic_term_id,a.class_level_id,a.stream_id,a.subject_id,CONCAT(te.first_name," ",te.last_name),cl.name,st.name,s.name,y.name,tm.name FROM teacher_assignments a JOIN teachers te ON te.id=a.teacher_id AND te.tenant_id=a.tenant_id JOIN class_levels cl ON cl.id=a.class_level_id AND cl.tenant_id=a.tenant_id LEFT JOIN streams st ON st.id=a.stream_id AND st.tenant_id=a.tenant_id JOIN subjects s ON s.id=a.subject_id AND s.tenant_id=a.tenant_id JOIN academic_years y ON y.id=a.academic_year_id AND y.tenant_id=a.tenant_id JOIN academic_terms tm ON tm.id=a.academic_term_id AND tm.tenant_id=a.tenant_id WHERE a.tenant_id=%s';args=[sid(t)]
    for c,v in [('academic_year_id',year_id),('academic_term_id',term_id),('teacher_id',teacher_id),('class_level_id',class_level_id)]:
        if v:sql+=f' AND a.{c}=%s';args.append(sid(v))
    sql+=' ORDER BY y.start_date,tm.term_number,cl.level_order,cl.name,st.name,s.name,te.last_name';pool=get_pool()
    async with pool.acquire() as c:
        async with c.cursor() as cur:await cur.execute(sql,args);rows=await cur.fetchall()
    return [rowdict(r,['id','teacher_id','academic_year_id','academic_term_id','class_level_id','stream_id','subject_id','teacher_name','class_name','stream_name','subject_name','academic_year_name','academic_term_name']) for r in rows]
async def create_assignment(t,p):
    pool=get_pool();i=uuid4()
    async with pool.acquire() as c:
        async with c.cursor() as cur:
            for table,key,label in [('teachers','teacher_id','Teacher'),('academic_years','academic_year_id','Academic year'),('academic_terms','academic_term_id','Academic term'),('class_levels','class_level_id','Class level'),('subjects','subject_id','Subject')]:
                if not await exists(cur,table,t,p[key]):raise HTTPException(404,f'{label} not found')
            await cur.execute('SELECT academic_year_id FROM academic_terms WHERE id=%s AND tenant_id=%s',(sid(p['academic_term_id']),sid(t)));r=await cur.fetchone()
            if not r or sid(r[0])!=sid(p['academic_year_id']):raise HTTPException(400,'Academic term does not belong to the selected academic year')
            if p.get('stream_id'):
                await cur.execute('SELECT class_level_id FROM streams WHERE id=%s AND tenant_id=%s',(sid(p['stream_id']),sid(t)));r=await cur.fetchone()
                if not r or sid(r[0])!=sid(p['class_level_id']):raise HTTPException(400,'Stream does not belong to the selected class level')
            await cur.execute('SELECT 1 FROM class_subjects WHERE tenant_id=%s AND class_level_id=%s AND subject_id=%s',(sid(t),sid(p['class_level_id']),sid(p['subject_id'])))
            if not await cur.fetchone():raise HTTPException(400,'Subject is not assigned to this class level')
            await cur.execute('SELECT 1 FROM teacher_assignments WHERE tenant_id=%s AND teacher_id=%s AND academic_term_id=%s AND class_level_id=%s AND (stream_id <=> %s) AND subject_id=%s',(sid(t),sid(p['teacher_id']),sid(p['academic_term_id']),sid(p['class_level_id']),sid(p.get('stream_id')),sid(p['subject_id'])))
            if await cur.fetchone():raise HTTPException(409,'This teacher assignment already exists')
            await cur.execute('INSERT INTO teacher_assignments (id,tenant_id,teacher_id,academic_year_id,academic_term_id,class_level_id,stream_id,subject_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',[sid(i),sid(t),sid(p['teacher_id']),sid(p['academic_year_id']),sid(p['academic_term_id']),sid(p['class_level_id']),sid(p.get('stream_id')),sid(p['subject_id'])])
    return next(x for x in await list_assignments(t) if x['id']==sid(i))
async def delete_assignment(t,i):
    pool=get_pool()
    async with pool.acquire() as c:
        async with c.cursor() as cur:await cur.execute('DELETE FROM teacher_assignments WHERE id=%s AND tenant_id=%s',(sid(i),sid(t)));rc=cur.rowcount
    if rc==0:raise HTTPException(404,'Teaching assignment not found')
async def list_rooms(t):
    pool=get_pool()
    async with pool.acquire() as c:
        async with c.cursor() as cur:await cur.execute('SELECT id,code,name,capacity,room_type,is_active FROM timetable_rooms WHERE tenant_id=%s ORDER BY name,code',(sid(t),));rows=await cur.fetchall()
    return [rowdict(r,['id','code','name','capacity','room_type','is_active']) for r in rows]
async def write_room(t,p,i=None):
    pool=get_pool();f=['code','name','capacity','room_type','is_active']
    async with pool.acquire() as c:
        async with c.cursor() as cur:
            try:
                if i:
                    if not await exists(cur,'timetable_rooms',t,i):raise HTTPException(404,'Room not found')
                    await cur.execute('UPDATE timetable_rooms SET '+','.join(f'{x}=%s' for x in f)+' WHERE id=%s AND tenant_id=%s',[*[p.get(x) for x in f],sid(i),sid(t)])
                else:i=uuid4();await cur.execute(f'INSERT INTO timetable_rooms (id,tenant_id,{",".join(f)}) VALUES (%s,%s,{",".join(["%s"]*len(f))})',[sid(i),sid(t),*[p.get(x) for x in f]])
            except Exception as e:
                if getattr(e,'args',[None])[0]==1062:raise HTTPException(409,'Room code already exists')
                raise
    return next(x for x in await list_rooms(t) if x['id']==sid(i))
async def create_room(t,p):return await write_room(t,p)
async def update_room(t,i,p):return await write_room(t,p,i)
async def list_periods(t):
    pool=get_pool()
    async with pool.acquire() as c:
        async with c.cursor() as cur:await cur.execute('SELECT id,code,name,start_time,end_time,is_break,sort_order,is_active FROM timetable_periods WHERE tenant_id=%s ORDER BY sort_order,start_time',(sid(t),));rows=await cur.fetchall()
    return [rowdict(r,['id','code','name','start_time','end_time','is_break','sort_order','is_active']) for r in rows]
async def write_period(t,p,i=None):
    if p['end_time']<=p['start_time']:raise HTTPException(400,'end_time must be after start_time')
    pool=get_pool();f=['code','name','start_time','end_time','is_break','sort_order','is_active']
    async with pool.acquire() as c:
        async with c.cursor() as cur:
            try:
                if i:
                    if not await exists(cur,'timetable_periods',t,i):raise HTTPException(404,'Period not found')
                    await cur.execute('UPDATE timetable_periods SET '+','.join(f'{x}=%s' for x in f)+' WHERE id=%s AND tenant_id=%s',[*[p.get(x) for x in f],sid(i),sid(t)])
                else:i=uuid4();await cur.execute(f'INSERT INTO timetable_periods (id,tenant_id,{",".join(f)}) VALUES (%s,%s,{",".join(["%s"]*len(f))})',[sid(i),sid(t),*[p.get(x) for x in f]])
            except Exception as e:
                if getattr(e,'args',[None])[0]==1062:raise HTTPException(409,'Period code already exists')
                raise
    return next(x for x in await list_periods(t) if x['id']==sid(i))
async def create_period(t,p):return await write_period(t,p)
async def update_period(t,i,p):return await write_period(t,p,i)
async def validate_tt(cur,t,p):
    for table,key,label in [('academic_years','academic_year_id','Academic year'),('academic_terms','academic_term_id','Academic term'),('class_levels','class_level_id','Class level'),('subjects','subject_id','Subject'),('teachers','teacher_id','Teacher'),('timetable_periods','period_id','Period')]:
        if not await exists(cur,table,t,p[key]):raise HTTPException(404,f'{label} not found')
    await cur.execute('SELECT academic_year_id FROM academic_terms WHERE id=%s AND tenant_id=%s',(sid(p['academic_term_id']),sid(t)));r=await cur.fetchone()
    if not r or sid(r[0])!=sid(p['academic_year_id']):raise HTTPException(400,'Academic term does not belong to the selected academic year')
    if p.get('stream_id'):
        await cur.execute('SELECT class_level_id FROM streams WHERE id=%s AND tenant_id=%s',(sid(p['stream_id']),sid(t)));r=await cur.fetchone()
        if not r or sid(r[0])!=sid(p['class_level_id']):raise HTTPException(400,'Stream does not belong to the selected class level')
    await cur.execute('SELECT 1 FROM teacher_assignments WHERE tenant_id=%s AND teacher_id=%s AND academic_term_id=%s AND class_level_id=%s AND (stream_id <=> %s) AND subject_id=%s',(sid(t),sid(p['teacher_id']),sid(p['academic_term_id']),sid(p['class_level_id']),sid(p.get('stream_id')),sid(p['subject_id'])))
    if not await cur.fetchone():raise HTTPException(400,'Teacher is not assigned to this subject/class/stream for the selected term')
    if p.get('room_id') and not await exists(cur,'timetable_rooms',t,p['room_id']):raise HTTPException(404,'Room not found')
async def slot_conflict(cur,t,p):
    await cur.execute('SELECT 1 FROM timetable_entries WHERE tenant_id=%s AND academic_term_id=%s AND class_level_id=%s AND (stream_id <=> %s) AND day_of_week=%s AND period_id=%s LIMIT 1',(sid(t),sid(p['academic_term_id']),sid(p['class_level_id']),sid(p.get('stream_id')),p['day_of_week'],sid(p['period_id'])))
    if await cur.fetchone():return 'class'
    await cur.execute('SELECT 1 FROM timetable_entries WHERE tenant_id=%s AND academic_term_id=%s AND teacher_id=%s AND day_of_week=%s AND period_id=%s LIMIT 1',(sid(t),sid(p['academic_term_id']),sid(p['teacher_id']),p['day_of_week'],sid(p['period_id'])))
    if await cur.fetchone():return 'teacher'
    if p.get('room_id'):
        await cur.execute('SELECT 1 FROM timetable_entries WHERE tenant_id=%s AND academic_term_id=%s AND room_id=%s AND day_of_week=%s AND period_id=%s LIMIT 1',(sid(t),sid(p['academic_term_id']),sid(p['room_id']),p['day_of_week'],sid(p['period_id'])))
        if await cur.fetchone():return 'room'
    return None
async def list_timetable(t,term_id=None,class_level_id=None,stream_id=None,day_of_week=None):
    sql='SELECT e.id,e.academic_year_id,e.academic_term_id,e.class_level_id,e.stream_id,e.subject_id,e.teacher_id,e.room_id,e.period_id,e.day_of_week,e.is_double,e.notes,CONCAT(te.first_name," ",te.last_name),cl.name,st.name,s.name,r.name,p.name FROM timetable_entries e JOIN teachers te ON te.id=e.teacher_id AND te.tenant_id=e.tenant_id JOIN class_levels cl ON cl.id=e.class_level_id AND cl.tenant_id=e.tenant_id LEFT JOIN streams st ON st.id=e.stream_id AND st.tenant_id=e.tenant_id JOIN subjects s ON s.id=e.subject_id AND s.tenant_id=e.tenant_id LEFT JOIN timetable_rooms r ON r.id=e.room_id AND r.tenant_id=e.tenant_id JOIN timetable_periods p ON p.id=e.period_id AND p.tenant_id=e.tenant_id WHERE e.tenant_id=%s';args=[sid(t)]
    for c,v in [('academic_term_id',term_id),('class_level_id',class_level_id),('stream_id',stream_id),('day_of_week',day_of_week)]:
        if v is not None:sql+=f' AND e.{c}=%s';args.append(sid(v))
    sql+=' ORDER BY e.day_of_week,p.sort_order,p.start_time,cl.level_order,cl.name,st.name';pool=get_pool()
    async with pool.acquire() as c:
        async with c.cursor() as cur:await cur.execute(sql,args);rows=await cur.fetchall()
    return [rowdict(r,['id','academic_year_id','academic_term_id','class_level_id','stream_id','subject_id','teacher_id','room_id','period_id','day_of_week','is_double','notes','teacher_name','class_name','stream_name','subject_name','room_name','period_name']) for r in rows]
async def create_timetable(t,p):
    pool=get_pool();i=uuid4()
    async with pool.acquire() as c:
        async with c.cursor() as cur:
            await validate_tt(cur,t,p);conf=await slot_conflict(cur,t,p)
            if conf:raise HTTPException(409,f'Timetable conflict: {conf} is already occupied in this period')
            try:await cur.execute('INSERT INTO timetable_entries (id,tenant_id,academic_year_id,academic_term_id,class_level_id,stream_id,subject_id,teacher_id,room_id,period_id,day_of_week,is_double,notes) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',[sid(i),sid(t),sid(p['academic_year_id']),sid(p['academic_term_id']),sid(p['class_level_id']),sid(p.get('stream_id')),sid(p['subject_id']),sid(p['teacher_id']),sid(p.get('room_id')),sid(p['period_id']),p['day_of_week'],p.get('is_double',False),p.get('notes')])
            except Exception as e:
                if getattr(e,'args',[None])[0]==1062:raise HTTPException(409,'Timetable slot conflict')
                raise
    return next(x for x in await list_timetable(t) if x['id']==sid(i))
async def delete_timetable(t,i):
    pool=get_pool()
    async with pool.acquire() as c:
        async with c.cursor() as cur:await cur.execute('DELETE FROM timetable_entries WHERE id=%s AND tenant_id=%s',(sid(i),sid(t)));rc=cur.rowcount
    if rc==0:raise HTTPException(404,'Timetable entry not found')
async def generate_timetable(t,req):
    pool=get_pool();created=skipped=0;conflicts=[]
    async with pool.acquire() as c:
        async with c.cursor() as cur:
            if req.get('replace_existing'):
                sql='DELETE FROM timetable_entries WHERE tenant_id=%s AND academic_term_id=%s';a=[sid(t),sid(req['academic_term_id'])]
                if req.get('class_level_id'):sql+=' AND class_level_id=%s';a.append(sid(req['class_level_id']))
                if req.get('stream_id'):sql+=' AND stream_id=%s';a.append(sid(req['stream_id']))
                await cur.execute(sql,a)
            sql='SELECT id,teacher_id,academic_year_id,academic_term_id,class_level_id,stream_id,subject_id FROM teacher_assignments WHERE tenant_id=%s AND academic_year_id=%s AND academic_term_id=%s';a=[sid(t),sid(req['academic_year_id']),sid(req['academic_term_id'])]
            if req.get('class_level_id'):sql+=' AND class_level_id=%s';a.append(sid(req['class_level_id']))
            if req.get('stream_id'):sql+=' AND stream_id=%s';a.append(sid(req['stream_id']))
            await cur.execute(sql,a);assigns=await cur.fetchall();await cur.execute('SELECT id FROM timetable_periods WHERE tenant_id=%s AND is_active=1 AND is_break=0 ORDER BY sort_order,start_time',(sid(t),));periods=[r[0] for r in await cur.fetchall()]
            if not periods:raise HTTPException(400,'No active teaching periods are configured')
            for x in assigns:
                placed=0
                for day in range(1,6):
                    for period in periods:
                        if placed>=req['lessons_per_week']:break
                        p={'academic_year_id':x[2],'academic_term_id':x[3],'class_level_id':x[4],'stream_id':x[5],'subject_id':x[6],'teacher_id':x[1],'room_id':None,'period_id':period,'day_of_week':day}
                        if await slot_conflict(cur,t,p):continue
                        await cur.execute('INSERT INTO timetable_entries (id,tenant_id,academic_year_id,academic_term_id,class_level_id,stream_id,subject_id,teacher_id,period_id,day_of_week) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',[str(uuid4()),sid(t),sid(x[2]),sid(x[3]),sid(x[4]),sid(x[5]),sid(x[6]),sid(x[1]),sid(period),day]);created+=1;placed+=1
                    if placed>=req['lessons_per_week']:break
                if placed<req['lessons_per_week']:skipped+=req['lessons_per_week']-placed;conflicts.append(f'Could not place {req["lessons_per_week"]-placed} lesson(s) for assignment {x[0]}')
    return {'created':created,'skipped':skipped,'conflicts':conflicts}
