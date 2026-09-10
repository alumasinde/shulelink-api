from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from fastapi import HTTPException
from app.core.database import get_pool


def sid(v): return str(v) if v is not None else None

def utcnow(): return datetime.now(timezone.utc).replace(tzinfo=None)

def naive(v): return v.astimezone(timezone.utc).replace(tzinfo=None) if v and v.tzinfo else v

async def exists(cur, table, tenant_id, item_id):
    await cur.execute(f"SELECT 1 FROM {table} WHERE id=%s AND tenant_id=%s LIMIT 1", (sid(item_id),sid(tenant_id)))
    return await cur.fetchone() is not None

async def session_for_update(cur, tenant_id, session_id):
    await cur.execute("SELECT id,academic_year_id,academic_term_id,class_level_id,stream_id,timetable_entry_id,session_type,session_date,scheduled_start_at,scheduled_end_at,actual_started_at,closed_at,status,attendance_policy_id FROM attendance_sessions WHERE id=%s AND tenant_id=%s FOR UPDATE",(sid(session_id),sid(tenant_id)))
    return await cur.fetchone()

async def resolve_policy(cur, tenant_id, session):
    await cur.execute("SELECT id,grace_period_minutes FROM attendance_policies WHERE tenant_id=%s AND enabled=1 AND (effective_from IS NULL OR effective_from<=%s) AND (effective_to IS NULL OR effective_to>=%s) ORDER BY version DESC,created_at DESC LIMIT 1",(sid(tenant_id),session[7],session[7]))
    return await cur.fetchone()

async def create_session(tenant_id, user_id, p):
    pool=get_pool(); i=uuid4()
    async with pool.acquire() as c:
        await c.begin()
        try:
            async with c.cursor() as cur:
                for table,key,label in [("academic_years","academic_year_id","Academic year"),("academic_terms","academic_term_id","Academic term"),("class_levels","class_level_id","Class level")]:
                    if p.get(key) and not await exists(cur,table,tenant_id,p[key]): raise HTTPException(404,f"{label} not found")
                if p.get("stream_id"):
                    await cur.execute("SELECT class_level_id FROM streams WHERE id=%s AND tenant_id=%s",(sid(p["stream_id"]),sid(tenant_id))); r=await cur.fetchone()
                    if not r: raise HTTPException(404,"Stream not found")
                    if sid(r[0])!=sid(p["class_level_id"]): raise HTTPException(400,"Stream does not belong to the selected class level")
                if p.get("academic_term_id") and p.get("academic_year_id"):
                    await cur.execute("SELECT academic_year_id FROM academic_terms WHERE id=%s AND tenant_id=%s",(sid(p["academic_term_id"]),sid(tenant_id))); r=await cur.fetchone()
                    if not r or sid(r[0])!=sid(p["academic_year_id"]): raise HTTPException(400,"Academic term does not belong to the selected academic year")
                if p.get("timetable_entry_id") and not await exists(cur,"timetable_entries",tenant_id,p["timetable_entry_id"]): raise HTTPException(404,"Timetable entry not found")
                policy=await resolve_policy(cur,tenant_id,[None,None,None,p["class_level_id"],p.get("stream_id"),None,p["session_type"],p["session_date"]]); pid=policy[0] if policy else None
                await cur.execute("SELECT id FROM attendance_sessions WHERE tenant_id=%s AND session_date=%s AND session_type=%s AND (class_level_id <=> %s) AND (stream_id <=> %s) AND (timetable_entry_id <=> %s) AND status<>'cancelled' LIMIT 1",(sid(tenant_id),p["session_date"],p["session_type"],sid(p["class_level_id"]),sid(p.get("stream_id")),sid(p.get("timetable_entry_id"))))
                if await cur.fetchone(): raise HTTPException(409,"An attendance session already exists for this class, date and lesson")
                await cur.execute("INSERT INTO attendance_sessions (id,tenant_id,academic_year_id,academic_term_id,class_level_id,stream_id,timetable_entry_id,session_type,session_date,scheduled_start_at,scheduled_end_at,actual_started_at,status,attendance_policy_id,opened_by_user_id,notes) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'open',%s,%s,%s)",(sid(i),sid(tenant_id),sid(p.get("academic_year_id")),sid(p.get("academic_term_id")),sid(p["class_level_id"]),sid(p.get("stream_id")),sid(p.get("timetable_entry_id")),p["session_type"],p["session_date"],p.get("scheduled_start_at"),p.get("scheduled_end_at"),p.get("scheduled_start_at"),sid(pid),sid(user_id),p.get("notes")))
            await c.commit()
        except: await c.rollback(); raise
    return i

async def get_session(tenant_id, session_id):
    pool=get_pool()
    async with pool.acquire() as c:
        async with c.cursor() as cur:
            await cur.execute("SELECT id,academic_year_id,academic_term_id,class_level_id,stream_id,timetable_entry_id,session_type,session_date,scheduled_start_at,scheduled_end_at,actual_started_at,closed_at,status,attendance_policy_id FROM attendance_sessions WHERE id=%s AND tenant_id=%s",(sid(session_id),sid(tenant_id))); r=await cur.fetchone()
            if not r: raise HTTPException(404,"Attendance session not found")
            await cur.execute("SELECT COUNT(*) FROM student_enrollments WHERE tenant_id=%s AND class_level_id=%s AND (stream_id <=> %s) AND enrollment_date<=%s AND (exit_date IS NULL OR exit_date>=%s) AND status='active'",(sid(tenant_id),sid(r[3]),sid(r[4]),r[7],r[7])); roster=(await cur.fetchone())[0]
            await cur.execute("SELECT COUNT(*) FROM attendance_records WHERE tenant_id=%s AND session_id=%s",(sid(tenant_id),sid(session_id))); marked=(await cur.fetchone())[0]
    keys=['id','academic_year_id','academic_term_id','class_level_id','stream_id','timetable_entry_id','session_type','session_date','scheduled_start_at','scheduled_end_at','actual_started_at','closed_at','status','attendance_policy_id']; d=dict(zip(keys,r)); d.update(roster_count=roster,marked_count=marked); return d

async def roster(tenant_id, session_id):
    pool=get_pool()
    async with pool.acquire() as c:
        async with c.cursor() as cur:
            await cur.execute("SELECT class_level_id,stream_id,session_date FROM attendance_sessions WHERE id=%s AND tenant_id=%s",(sid(session_id),sid(tenant_id))); s=await cur.fetchone()
            if not s: raise HTTPException(404,"Attendance session not found")
            await cur.execute("SELECT e.id,e.student_id,e.class_level_id,e.stream_id,st.admission_number,st.first_name,st.middle_name,st.last_name,COALESCE(a.code,'not_marked'),COALESCE(a.name,'Not Marked'),ar.late_minutes,ar.marked_at,ar.remarks FROM student_enrollments e JOIN students st ON st.id=e.student_id AND st.tenant_id=e.tenant_id LEFT JOIN attendance_records ar ON ar.session_id=%s AND ar.student_id=e.student_id AND ar.tenant_id=%s LEFT JOIN attendance_statuses a ON a.id=ar.attendance_status_id AND a.tenant_id=ar.tenant_id WHERE e.tenant_id=%s AND e.class_level_id=%s AND (e.stream_id <=> %s) AND e.enrollment_date<=%s AND (e.exit_date IS NULL OR e.exit_date>=%s) AND e.status='active' ORDER BY st.last_name,st.first_name,st.admission_number",(sid(session_id),sid(tenant_id),sid(tenant_id),sid(s[0]),sid(s[1]),s[2],s[2])); rows=await cur.fetchall()
    keys=['enrollment_id','student_id','class_level_id','stream_id','admission_number','first_name','middle_name','last_name','status_code','status_name','late_minutes','marked_at','remarks']; return [dict(zip(keys,x)) for x in rows]

async def mark(tenant_id,user_id,session_id,payload,idempotency_key):
    if idempotency_key and not 1<=len(idempotency_key.strip())<=191: raise HTTPException(422,"X-Idempotency-Key must contain 1-191 characters")
    pool=get_pool()
    async with pool.acquire() as c:
        await c.begin()
        try:
            async with c.cursor() as cur:
                s=await session_for_update(cur,tenant_id,session_id)
                if not s: raise HTTPException(404,"Attendance session not found")
                if s[12]!='open': raise HTTPException(409,f"Attendance session is {s[12]} and cannot be modified")
                if idempotency_key:
                    await cur.execute("SELECT id FROM attendance_events WHERE tenant_id=%s AND idempotency_key=%s LIMIT 1 FOR UPDATE",(sid(tenant_id),idempotency_key.strip()))
                    if await cur.fetchone(): await c.commit(); return {'session_id':session_id,'processed':0,'created':0,'updated':0,'results':[]}
                ids=[sid(x.student_id) for x in payload.items]; ph=','.join(['%s']*len(ids))
                await cur.execute(f"SELECT student_id FROM student_enrollments WHERE tenant_id=%s AND class_level_id=%s AND (stream_id <=> %s) AND enrollment_date<=%s AND (exit_date IS NULL OR exit_date>=%s) AND status='active' AND student_id IN ({ph})",[sid(tenant_id),sid(s[3]),sid(s[4]),s[7],s[7],*ids]); valid={sid(x[0]) for x in await cur.fetchall()}
                if len(valid)!=len(set(ids)): raise HTTPException(422,"One or more students are not enrolled in this session's class/stream on the session date")
                created=updated=0; results=[]
                for item in payload.items:
                    await cur.execute("SELECT id,attendance_status_id,ast.code FROM attendance_records ar JOIN attendance_statuses ast ON ast.id=ar.attendance_status_id AND ast.tenant_id=ar.tenant_id WHERE ar.tenant_id=%s AND ar.session_id=%s AND ar.student_id=%s FOR UPDATE",(sid(tenant_id),sid(session_id),sid(item.student_id))); old=await cur.fetchone()
                    await cur.execute("SELECT id,code FROM attendance_statuses WHERE tenant_id=%s AND code=%s AND is_active=1 LIMIT 1",(sid(tenant_id),item.status_code)); st=await cur.fetchone()
                    if not st: raise HTTPException(422,f"Attendance status '{item.status_code}' is not active")
                    at=naive(item.marked_at or utcnow()); late=None; code=st[1]
                    if code in ('present','late') and s[8] is not None:
                        await cur.execute("SELECT grace_period_minutes FROM attendance_policies WHERE tenant_id=%s AND enabled=1 AND (effective_from IS NULL OR effective_from<=%s) AND (effective_to IS NULL OR effective_to>=%s) ORDER BY version DESC,created_at DESC LIMIT 1",(sid(tenant_id),s[7],s[7])); pol=await cur.fetchone(); grace=int(pol[0]) if pol else 0
                        late=max(0,int((at-naive(s[8])).total_seconds()//60))
                        if code=='present' and late>grace:
                            code='late'; await cur.execute("SELECT id FROM attendance_statuses WHERE tenant_id=%s AND code='late' AND is_active=1",(sid(tenant_id),)); st=( (await cur.fetchone())[0], 'late')
                        elif code=='present': late=None
                    if old:
                        await cur.execute("UPDATE attendance_records SET attendance_status_id=%s,marked_at=%s,marked_by_user_id=%s,source=%s,late_minutes=%s,remarks=%s,is_correction=%s WHERE id=%s AND tenant_id=%s",(sid(st[0]),at,sid(user_id),payload.source,late,item.remarks,1 if old[2]!=code else 0,sid(old[0]),sid(tenant_id))); updated+=1; rid=old[0]
                    else:
                        rid=uuid4(); await cur.execute("INSERT INTO attendance_records (id,tenant_id,session_id,student_id,attendance_status_id,marked_at,marked_by_user_id,source,late_minutes,remarks) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(sid(rid),sid(tenant_id),sid(session_id),sid(item.student_id),sid(st[0]),at,sid(user_id),payload.source,late,item.remarks)); created+=1
                    results.append({'student_id':item.student_id,'status_code':code,'late_minutes':late,'record_id':rid})
                await cur.execute("INSERT INTO attendance_events (id,tenant_id,session_id,event_type,source,occurred_at,actor_user_id,idempotency_key) VALUES (%s,%s,%s,'captured',%s,%s,%s,%s)",(sid(uuid4()),sid(tenant_id),sid(session_id),payload.source,utcnow(),sid(user_id),idempotency_key.strip() if idempotency_key else None))
            await c.commit(); return {'session_id':session_id,'processed':len(results),'created':created,'updated':updated,'results':results}
        except: await c.rollback(); raise

async def close(tenant_id,user_id,session_id):
    pool=get_pool()
    async with pool.acquire() as c:
        await c.begin()
        try:
            async with c.cursor() as cur:
                s=await session_for_update(cur,tenant_id,session_id)
                if not s: raise HTTPException(404,"Attendance session not found")
                if s[12]!='open': raise HTTPException(409,f"Attendance session is already {s[12]}")
                now=utcnow(); await cur.execute("UPDATE attendance_sessions SET status='closed',closed_at=%s,closed_by_user_id=%s WHERE id=%s AND tenant_id=%s",(now,sid(user_id),sid(session_id),sid(tenant_id)))
            await c.commit(); return {'id':session_id,'status':'closed','closed_at':now}
        except: await c.rollback(); raise
