from uuid import UUID, uuid4
from fastapi import HTTPException
from app.core.database import get_pool

TABLES={
 'campuses':(['code','name','address','phone','email','is_main'],'id,tenant_id,code,name,address,phone,email,is_main,is_active'),
 'academic_years':(['name','start_date','end_date','is_current'],'id,tenant_id,name,start_date,end_date,is_current,is_active'),
 'academic_terms':(['academic_year_id','name','term_number','start_date','end_date','is_current'],'id,tenant_id,academic_year_id,name,term_number,start_date,end_date,is_current,is_active'),
 'departments':(['code','name','description'],'id,tenant_id,code,name,description,is_active'),
 'class_levels':(['code','name','level_order'],'id,tenant_id,code,name,level_order,is_active'),
 'streams':(['class_level_id','code','name','capacity'],'id,tenant_id,class_level_id,code,name,capacity,is_active'),
 'subjects':(['department_id','code','name','short_name','subject_type','learning_area_id'],'id,tenant_id,department_id,code,name,short_name,subject_type,learning_area_id,is_active'),
}

def _value(v): return v.isoformat() if hasattr(v,'isoformat') else (str(v) if isinstance(v,UUID) else v)

def _row(keys,row):
    d={k:row[i] for i,k in enumerate(keys)}
    for k,v in list(d.items()):
        if k in {'id','tenant_id','academic_year_id','class_level_id','subject_id','department_id','learning_area_id'} and v is not None: d[k]=str(v)
        if k in {'is_main','is_current','is_active','is_compulsory'}: d[k]=bool(v)
    return d

async def list_items(table:str,tenant_id:UUID):
    _,cols=TABLES[table]; pool=get_pool()
    async with pool.acquire() as conn:
      async with conn.cursor() as cur:
        order='name' if table not in {'academic_years'} else 'start_date'
        await cur.execute(f'SELECT {cols} FROM {table} WHERE tenant_id=%s ORDER BY {order}', (str(tenant_id),)); rows=await cur.fetchall()
    keys=[x.strip() for x in cols.split(',')]
    return [_row(keys,r) for r in rows]

async def create_item(table:str,tenant_id:UUID,payload:dict):
    fields=TABLES[table][0]; data={k:payload.get(k) for k in fields}; data['id']=uuid4(); data['tenant_id']=tenant_id
    if table=='academic_terms':
        pool=get_pool()
        async with pool.acquire() as conn:
          async with conn.cursor() as cur:
            await cur.execute('SELECT tenant_id FROM academic_years WHERE id=%s', (str(data['academic_year_id']),)); row=await cur.fetchone()
            if not row or str(row[0])!=str(tenant_id): raise HTTPException(404,'Academic year not found')
    if table=='streams':
        pool=get_pool()
        async with pool.acquire() as conn:
          async with conn.cursor() as cur:
            await cur.execute('SELECT tenant_id FROM class_levels WHERE id=%s',(str(data['class_level_id']),)); row=await cur.fetchone()
            if not row or str(row[0])!=str(tenant_id): raise HTTPException(404,'Class level not found')
    if table=='subjects':
        pool=get_pool()
        async with pool.acquire() as conn:
          async with conn.cursor() as cur:
            if data.get('department_id'):
                await cur.execute('SELECT tenant_id FROM departments WHERE id=%s',(str(data['department_id']),)); row=await cur.fetchone()
                if not row or str(row[0])!=str(tenant_id): raise HTTPException(404,'Department not found')
            if data.get('learning_area_id'):
                await cur.execute('SELECT tenant_id FROM learning_areas WHERE id=%s',(str(data['learning_area_id']),)); row=await cur.fetchone()
                if not row or str(row[0])!=str(tenant_id): raise HTTPException(404,'Learning area not found')
    if table=='academic_years' and data['is_current']: await _clear_current('academic_years',tenant_id)
    if table=='academic_terms' and data['is_current']: await _clear_current('academic_terms',tenant_id)
    pool=get_pool(); cols=', '.join(['id','tenant_id']+fields); marks=', '.join(['%s']*(2+len(fields))); vals=[str(data['id']),str(tenant_id)]+[_value(data[f]) for f in fields]
    try:
      async with pool.acquire() as conn:
       async with conn.cursor() as cur: await cur.execute(f'INSERT INTO {table} ({cols}) VALUES ({marks})',vals)
    except Exception as exc:
      if getattr(exc,'args',[None])[0] in (1062,): raise HTTPException(409,'A record with the same unique value already exists')
      raise
    return await get_item(table,tenant_id,data['id'])

async def _clear_current(table,tenant_id):
    pool=get_pool()
    async with pool.acquire() as conn:
      async with conn.cursor() as cur: await cur.execute(f'UPDATE {table} SET is_current=0 WHERE tenant_id=%s',(str(tenant_id),))

async def get_item(table,tenant_id,item_id):
    _,cols=TABLES[table]; pool=get_pool()
    async with pool.acquire() as conn:
      async with conn.cursor() as cur:
       await cur.execute(f'SELECT {cols} FROM {table} WHERE id=%s AND tenant_id=%s',(str(item_id),str(tenant_id))); row=await cur.fetchone()
    if not row: raise HTTPException(404,'Record not found')
    return _row([x.strip() for x in cols.split(',')],row)

async def assign_subject(tenant_id, payload):
    cid,sid=str(payload['class_level_id']),str(payload['subject_id']); pool=get_pool()
    async with pool.acquire() as conn:
      async with conn.cursor() as cur:
        await cur.execute('SELECT 1 FROM class_levels WHERE id=%s AND tenant_id=%s',(cid,str(tenant_id))); a=await cur.fetchone()
        await cur.execute('SELECT 1 FROM subjects WHERE id=%s AND tenant_id=%s',(sid,str(tenant_id))); b=await cur.fetchone()
        if not a or not b: raise HTTPException(404,'Class level or subject not found')
        try:
            await cur.execute('''INSERT INTO class_subjects
                (id,tenant_id,class_level_id,subject_id,is_compulsory,curriculum_version_id,grade_id,requirement_type,weekly_periods)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
                (str(uuid4()),str(tenant_id),cid,sid,payload.get('is_compulsory',True),_value(payload.get('curriculum_version_id')),_value(payload.get('grade_id')),payload.get('requirement_type','required'),payload.get('weekly_periods')))
        except Exception as exc:
          if getattr(exc,'args',[None])[0]==1062: raise HTTPException(409,'Subject is already assigned to this class')
          raise
        await cur.execute('SELECT id,class_level_id,subject_id,is_compulsory,curriculum_version_id,grade_id,requirement_type,weekly_periods FROM class_subjects WHERE tenant_id=%s AND class_level_id=%s AND subject_id=%s',(str(tenant_id),cid,sid)); row=await cur.fetchone()
    return {'id':str(row[0]),'class_level_id':str(row[1]),'subject_id':str(row[2]),'is_compulsory':bool(row[3]),'curriculum_version_id':str(row[4]) if row[4] else None,'grade_id':str(row[5]) if row[5] else None,'requirement_type':row[6],'weekly_periods':float(row[7]) if row[7] is not None else None}

async def list_assignments(tenant_id):
    pool=get_pool()
    async with pool.acquire() as conn:
      async with conn.cursor() as cur:
       await cur.execute('''SELECT cs.id,cs.class_level_id,cs.subject_id,cs.is_compulsory,cl.name,s.name,cs.curriculum_version_id,cs.grade_id,cs.requirement_type,cs.weekly_periods
         FROM class_subjects cs JOIN class_levels cl ON cl.id=cs.class_level_id AND cl.tenant_id=cs.tenant_id
         JOIN subjects s ON s.id=cs.subject_id AND s.tenant_id=cs.tenant_id
         WHERE cs.tenant_id=%s ORDER BY cl.level_order,cl.name,s.name''',(str(tenant_id),)); rows=await cur.fetchall()
    return [{'id':str(r[0]),'class_level_id':str(r[1]),'subject_id':str(r[2]),'is_compulsory':bool(r[3]),'class_name':r[4],'subject_name':r[5],'curriculum_version_id':str(r[6]) if r[6] else None,'grade_id':str(r[7]) if r[7] else None,'requirement_type':r[8],'weekly_periods':float(r[9]) if r[9] is not None else None} for r in rows]

async def list_settings(tenant_id):
    pool=get_pool()
    async with pool.acquire() as conn:
      async with conn.cursor() as cur: await cur.execute('SELECT setting_key,setting_value,value_type FROM school_settings WHERE tenant_id=%s ORDER BY setting_key',(str(tenant_id),)); rows=await cur.fetchall()
    return [{'setting_key':r[0],'setting_value':r[1],'value_type':r[2]} for r in rows]

async def upsert_setting(tenant_id,key,payload,user_id):
    pool=get_pool(); value=payload.get('value'); typ=payload.get('value_type','string')
    async with pool.acquire() as conn:
      async with conn.cursor() as cur:
       await cur.execute('INSERT INTO school_settings (id,tenant_id,setting_key,setting_value,value_type,updated_by) VALUES (%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE setting_value=VALUES(setting_value),value_type=VALUES(value_type),updated_by=VALUES(updated_by)',(str(uuid4()),str(tenant_id),key,value,typ,str(user_id)))
    return {'setting_key':key,'setting_value':value,'value_type':typ}
