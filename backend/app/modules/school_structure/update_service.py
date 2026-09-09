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

async def update_item(table,tenant_id,item_id,data):
    if table not in FIELDS: raise HTTPException(400,'Unsupported record type')
    data={k:v for k,v in data.items() if k in FIELDS[table]}
    if not data: return await get_item(table,tenant_id,item_id)
    pool=get_pool()
    async with pool.acquire() as conn:
        try:
            await conn.begin()
            async with conn.cursor() as cur:
                await cur.execute(f'SELECT * FROM {table} WHERE id=%s AND tenant_id=%s FOR UPDATE',(str(item_id),str(tenant_id)))
                row=await cur.fetchone()
                if not row: raise HTTPException(404,'Record not found')

                columns=[d[0] for d in cur.description]
                current=dict(zip(columns,row))
                final={**current,**data}

                if table=='academic_years' and final.get('end_date')<=final.get('start_date'):
                    raise HTTPException(422,'end_date must be after start_date')
                if table=='academic_terms':
                    await cur.execute('SELECT start_date,end_date FROM academic_years WHERE id=%s AND tenant_id=%s',(str(final['academic_year_id']),str(tenant_id)))
                    academic_year=await cur.fetchone()
                    if not academic_year: raise HTTPException(404,'Academic year not found')
                    if final.get('end_date')<=final.get('start_date'):
                        raise HTTPException(422,'end_date must be after start_date')
                    if final['start_date']<academic_year[0] or final['end_date']>academic_year[1]:
                        raise HTTPException(422,'Academic term dates must fall within the selected academic year')
                if table=='streams':
                    await cur.execute('SELECT id FROM class_levels WHERE id=%s AND tenant_id=%s',(str(final['class_level_id']),str(tenant_id)))
                    if not await cur.fetchone(): raise HTTPException(404,'Class level not found')
                if table=='subjects' and final.get('department_id'):
                    await cur.execute('SELECT id FROM departments WHERE id=%s AND tenant_id=%s',(str(final['department_id']),str(tenant_id)))
                    if not await cur.fetchone(): raise HTTPException(404,'Department not found')

                if table in {'academic_years','academic_terms'} and data.get('is_current') is True:
                    await cur.execute(f'UPDATE {table} SET is_current=0 WHERE tenant_id=%s AND id<>%s',(str(tenant_id),str(item_id)))

                assignments=','.join(f'{k}=%s' for k in data)
                try:
                    await cur.execute(f'UPDATE {table} SET {assignments} WHERE id=%s AND tenant_id=%s',[*[_value(v) for v in data.values()],str(item_id),str(tenant_id)])
                except Exception as exc:
                    if getattr(exc,'args',[None])[0]==1062: raise HTTPException(409,'A record with the same unique value already exists')
                    raise
            await conn.commit()
        except Exception:
            await conn.rollback()
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
