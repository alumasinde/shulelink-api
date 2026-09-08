from uuid import UUID
from fastapi import HTTPException
from app.core.database import get_pool
from app.modules.school_structure.service import get_item

FIELDS={
 'campuses':{'code','name','address','phone','email','is_main','is_active'},
 'academic_years':{'name','start_date','end_date','is_current','is_active'},
 'academic_terms':{'academic_year_id','name','term_number','start_date','end_date','is_current','is_active'},
 'departments':{'code','name','description','is_active'},
 'class_levels':{'code','name','level_order','is_active'},
 'streams':{'class_level_id','code','name','capacity','is_active'},
 'subjects':{'department_id','code','name','short_name','subject_type','is_active'},
}

def _value(v): return str(v) if isinstance(v,UUID) else v

async def _clear_current(table,tenant_id,exclude_id=None):
    pool=get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            sql=f'UPDATE {table} SET is_current=0 WHERE tenant_id=%s'; args=[str(tenant_id)]
            if exclude_id: sql+=' AND id<>%s'; args.append(str(exclude_id))
            await cur.execute(sql,args)

async def update_item(table,tenant_id,item_id,data):
    if table not in FIELDS: raise HTTPException(400,'Unsupported record type')
    data={k:v for k,v in data.items() if k in FIELDS[table]}
    if not data: return await get_item(table,tenant_id,item_id)
    pool=get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f'SELECT id FROM {table} WHERE id=%s AND tenant_id=%s',(str(item_id),str(tenant_id)))
            if not await cur.fetchone(): raise HTTPException(404,'Record not found')
            if table=='academic_terms' and data.get('academic_year_id'):
                await cur.execute('SELECT id FROM academic_years WHERE id=%s AND tenant_id=%s',(str(data['academic_year_id']),str(tenant_id)))
                if not await cur.fetchone(): raise HTTPException(404,'Academic year not found')
            if table=='streams' and data.get('class_level_id'):
                await cur.execute('SELECT id FROM class_levels WHERE id=%s AND tenant_id=%s',(str(data['class_level_id']),str(tenant_id)))
                if not await cur.fetchone(): raise HTTPException(404,'Class level not found')
            if table=='subjects' and data.get('department_id'):
                await cur.execute('SELECT id FROM departments WHERE id=%s AND tenant_id=%s',(str(data['department_id']),str(tenant_id)))
                if not await cur.fetchone(): raise HTTPException(404,'Department not found')
    if table in {'academic_years','academic_terms'} and data.get('is_current') is True: await _clear_current(table,tenant_id,item_id)
    assignments=','.join(f'{k}=%s' for k in data)
    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(f'UPDATE {table} SET {assignments} WHERE id=%s AND tenant_id=%s',[*[_value(v) for v in data.values()],str(item_id),str(tenant_id)])
    except Exception as exc:
        if getattr(exc,'args',[None])[0]==1062: raise HTTPException(409,'A record with the same unique value already exists')
        raise
    return await get_item(table,tenant_id,item_id)

async def update_class_subject(tenant_id,item_id,is_compulsory):
    pool=get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('UPDATE class_subjects SET is_compulsory=%s WHERE id=%s AND tenant_id=%s',(bool(is_compulsory),str(item_id),str(tenant_id)))
            if cur.rowcount==0: raise HTTPException(404,'Class subject assignment not found')
            await cur.execute('SELECT id,class_level_id,subject_id,is_compulsory FROM class_subjects WHERE id=%s AND tenant_id=%s',(str(item_id),str(tenant_id)))
            row=await cur.fetchone()
    return {'id':str(row[0]),'class_level_id':str(row[1]),'subject_id':str(row[2]),'is_compulsory':bool(row[3])}

async def delete_class_subject(tenant_id,item_id):
    pool=get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('DELETE FROM class_subjects WHERE id=%s AND tenant_id=%s',(str(item_id),str(tenant_id)))
            if cur.rowcount==0: raise HTTPException(404,'Class subject assignment not found')
