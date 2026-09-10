from __future__ import annotations
from uuid import UUID, uuid4
from fastapi import HTTPException
from app.core.database import get_central_pool, get_pool
from app.modules.curriculum.schemas import CurriculumTemplateCreate, CurriculumTemplateUpdate, CurriculumTemplateCloneRequest, CurriculumSelectRequest


def _summary(row, counts):
    return {'id': UUID(str(row[0])), 'code': row[1], 'name': row[2], 'description': row[3], 'country_code': row[4], 'framework_code': row[5], 'version_no': int(row[6]), 'status': row[7], 'effective_from': row[8], 'effective_to': row[9], 'is_default': bool(row[10]), 'counts': counts}

async def _template_row(cur, template_id):
    await cur.execute('SELECT id,code,name,description,country_code,framework_code,version_no,status,effective_from,effective_to,is_default FROM platform_curriculum_templates WHERE id=%s', (str(template_id),))
    row = await cur.fetchone()
    if not row: raise HTTPException(404, 'Curriculum template not found')
    return row

async def _document(cur, template_id):
    tid=str(template_id)
    await cur.execute('SELECT id,code,name,sequence_no FROM platform_curriculum_levels WHERE template_id=%s ORDER BY sequence_no,code',(tid,)); levels=await cur.fetchall()
    await cur.execute('SELECT id,education_level_id,code,name,sequence_no FROM platform_curriculum_grades WHERE template_id=%s ORDER BY sequence_no,code',(tid,)); grades=await cur.fetchall()
    await cur.execute('SELECT id,code,name,description,sequence_no FROM platform_curriculum_learning_areas WHERE template_id=%s ORDER BY sequence_no,code',(tid,)); areas=await cur.fetchall()
    await cur.execute('SELECT id,learning_area_id,code,name,subject_type,description,sequence_no FROM platform_curriculum_subjects WHERE template_id=%s ORDER BY sequence_no,code',(tid,)); subjects=await cur.fetchall()
    await cur.execute('SELECT grade_id,subject_id,pathway_id,track_id,requirement_type,weekly_periods FROM platform_curriculum_subject_offerings WHERE template_id=%s',(tid,)); offerings=await cur.fetchall()
    await cur.execute('SELECT id,code,name,description,sequence_no FROM platform_curriculum_pathways WHERE template_id=%s ORDER BY sequence_no,code',(tid,)); pathways=await cur.fetchall()
    await cur.execute('SELECT id,pathway_id,code,name,description,sequence_no FROM platform_curriculum_tracks WHERE template_id=%s ORDER BY sequence_no,code',(tid,)); tracks=await cur.fetchall()
    await cur.execute('SELECT id,grade_id,pathway_id,track_id,code,name,description FROM platform_curriculum_subject_combinations WHERE template_id=%s ORDER BY code',(tid,)); combinations=await cur.fetchall()
    await cur.execute('SELECT combination_id,subject_id FROM platform_curriculum_combination_subjects WHERE combination_id IN (SELECT id FROM platform_curriculum_subject_combinations WHERE template_id=%s) ORDER BY sort_order,subject_id',(tid,)); combo_subjects=await cur.fetchall()
    level_codes={str(r[0]):r[1] for r in levels}; grade_codes={str(r[0]):r[2] for r in grades}; area_codes={str(r[0]):r[1] for r in areas}; subject_codes={str(r[0]):r[2] for r in subjects}; pathway_codes={str(r[0]):r[1] for r in pathways}; track_codes={str(r[0]):r[2] for r in tracks}; combo_map={}
    for r in combo_subjects: combo_map.setdefault(str(r[0]),[]).append(subject_codes.get(str(r[1]),str(r[1])))
    return {'levels':[{'code':r[1],'name':r[2],'sequence_no':r[3]} for r in levels],'grades':[{'code':r[2],'name':r[3],'education_level_code':level_codes.get(str(r[1]),str(r[1])),'sequence_no':r[4]} for r in grades],'learning_areas':[{'code':r[1],'name':r[2],'description':r[3],'sequence_no':r[4]} for r in areas],'subjects':[{'code':r[2],'name':r[3],'learning_area_code':area_codes.get(str(r[1])),'subject_type':r[4],'description':r[5],'sequence_no':r[6]} for r in subjects],'offerings':[{'grade_code':grade_codes.get(str(r[0]),str(r[0])),'subject_code':subject_codes.get(str(r[1]),str(r[1])),'pathway_code':pathway_codes.get(str(r[2])) if r[2] else None,'track_code':track_codes.get(str(r[3])) if r[3] else None,'requirement_type':r[4],'weekly_periods':float(r[5]) if r[5] is not None else None} for r in offerings],'pathways':[{'code':r[1],'name':r[2],'description':r[3],'sequence_no':r[4]} for r in pathways],'tracks':[{'pathway_code':pathway_codes.get(str(r[1]),str(r[1])),'code':r[2],'name':r[3],'description':r[4],'sequence_no':r[5]} for r in tracks],'combinations':[{'code':r[4],'name':r[5],'grade_code':grade_codes.get(str(r[1])) if r[1] else None,'pathway_code':pathway_codes.get(str(r[2])) if r[2] else None,'track_code':track_codes.get(str(r[3])) if r[3] else None,'description':r[6],'subjects':combo_map.get(str(r[0]),[])} for r in combinations]}

def _validate(doc):
    for items in (doc.levels,doc.grades,doc.learning_areas,doc.subjects,doc.pathways,doc.combinations):
        codes=[x.code for x in items]
        if len(codes)!=len(set(codes)): raise HTTPException(422,'Duplicate curriculum code detected')
    levels={x.code for x in doc.levels}; grades={x.code for x in doc.grades}; areas={x.code for x in doc.learning_areas}; subjects={x.code for x in doc.subjects}; pathways={x.code for x in doc.pathways}; tracks={(x.pathway_code,x.code) for x in doc.tracks}
    if any(x.education_level_code not in levels for x in doc.grades): raise HTTPException(422,'Grade references an unknown education level')
    if any(x.learning_area_code and x.learning_area_code not in areas for x in doc.subjects): raise HTTPException(422,'Subject references an unknown learning area')
    if any(x.pathway_code not in pathways for x in doc.tracks): raise HTTPException(422,'Track references an unknown pathway')
    for x in doc.offerings:
        if x.grade_code not in grades or x.subject_code not in subjects: raise HTTPException(422,'Offering references an unknown grade or subject')
        if x.pathway_code and x.pathway_code not in pathways: raise HTTPException(422,'Offering references an unknown pathway')
        if x.track_code and (x.pathway_code,x.track_code) not in tracks: raise HTTPException(422,'Offering references an unknown track')
    for x in doc.combinations:
        if x.grade_code and x.grade_code not in grades: raise HTTPException(422,'Combination references an unknown grade')
        if x.pathway_code and x.pathway_code not in pathways: raise HTTPException(422,'Combination references an unknown pathway')
        if x.track_code and (x.pathway_code,x.track_code) not in tracks: raise HTTPException(422,'Combination references an unknown track')
        if any(s not in subjects for s in x.subjects): raise HTTPException(422,'Combination contains an unknown subject')

async def _replace_document(cur, template_id, doc):
    _validate(doc); tid=str(template_id)
    for table in ('platform_curriculum_subject_offerings','platform_curriculum_combination_subjects','platform_curriculum_subject_combinations','platform_curriculum_subjects','platform_curriculum_learning_areas','platform_curriculum_tracks','platform_curriculum_pathways','platform_curriculum_grades','platform_curriculum_levels'):
        if table=='platform_curriculum_combination_subjects': await cur.execute('DELETE FROM '+table+' WHERE combination_id IN (SELECT id FROM platform_curriculum_subject_combinations WHERE template_id=%s)',(tid,))
        else: await cur.execute('DELETE FROM '+table+' WHERE template_id=%s',(tid,))
    def ids(items): return {x.code:str(uuid4()) for x in items}
    level_ids=ids(doc.levels); grade_ids=ids(doc.grades); area_ids=ids(doc.learning_areas); subject_ids=ids(doc.subjects); pathway_ids=ids(doc.pathways); combo_ids=ids(doc.combinations); track_ids={(x.pathway_code,x.code):str(uuid4()) for x in doc.tracks}
    for x in doc.levels: await cur.execute('INSERT INTO platform_curriculum_levels (id,template_id,code,name,sequence_no) VALUES (%s,%s,%s,%s,%s)',(level_ids[x.code],tid,x.code,x.name,x.sequence_no))
    for x in doc.grades: await cur.execute('INSERT INTO platform_curriculum_grades (id,template_id,education_level_id,code,name,sequence_no) VALUES (%s,%s,%s,%s,%s,%s)',(grade_ids[x.code],tid,level_ids[x.education_level_code],x.code,x.name,x.sequence_no))
    for x in doc.learning_areas: await cur.execute('INSERT INTO platform_curriculum_learning_areas (id,template_id,code,name,description,sequence_no) VALUES (%s,%s,%s,%s,%s,%s)',(area_ids[x.code],tid,x.code,x.name,x.description,x.sequence_no))
    for x in doc.subjects: await cur.execute('INSERT INTO platform_curriculum_subjects (id,template_id,learning_area_id,code,name,subject_type,description,sequence_no) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',(subject_ids[x.code],tid,area_ids.get(x.learning_area_code),x.code,x.name,x.subject_type,x.description,x.sequence_no))
    for x in doc.pathways: await cur.execute('INSERT INTO platform_curriculum_pathways (id,template_id,code,name,description,sequence_no) VALUES (%s,%s,%s,%s,%s,%s)',(pathway_ids[x.code],tid,x.code,x.name,x.description,x.sequence_no))
    for x in doc.tracks: await cur.execute('INSERT INTO platform_curriculum_tracks (id,template_id,pathway_id,code,name,description,sequence_no) VALUES (%s,%s,%s,%s,%s,%s,%s)',(track_ids[(x.pathway_code,x.code)],tid,pathway_ids[x.pathway_code],x.code,x.name,x.description,x.sequence_no))
    for x in doc.offerings: await cur.execute('INSERT INTO platform_curriculum_subject_offerings (id,template_id,grade_id,subject_id,pathway_id,track_id,requirement_type,weekly_periods) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',(str(uuid4()),tid,grade_ids[x.grade_code],subject_ids[x.subject_code],pathway_ids.get(x.pathway_code),track_ids.get((x.pathway_code,x.track_code)) if x.pathway_code and x.track_code else None,x.requirement_type,x.weekly_periods))
    for x in doc.combinations:
        await cur.execute('INSERT INTO platform_curriculum_subject_combinations (id,template_id,grade_id,pathway_id,track_id,code,name,description) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)',(combo_ids[x.code],tid,grade_ids.get(x.grade_code),pathway_ids.get(x.pathway_code),track_ids.get((x.pathway_code,x.track_code)) if x.pathway_code and x.track_code else None,x.code,x.name,x.description))
        for i,s in enumerate(x.subjects): await cur.execute('INSERT INTO platform_curriculum_combination_subjects (id,combination_id,subject_id,is_required,sort_order) VALUES (%s,%s,%s,1,%s)',(str(uuid4()),combo_ids[x.code],subject_ids[s],i))

async def list_templates(published_only=False):
    pool=get_central_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            sql='SELECT id,code,name,description,country_code,framework_code,version_no,status,effective_from,effective_to,is_default FROM platform_curriculum_templates'+(" WHERE status='published'" if published_only else '')+' ORDER BY is_default DESC,name,version_no DESC'
            await cur.execute(sql); rows=await cur.fetchall(); result=[]
            for row in rows:
                counts={}
                for key,table in (('levels','platform_curriculum_levels'),('grades','platform_curriculum_grades'),('subjects','platform_curriculum_subjects'),('pathways','platform_curriculum_pathways'),('tracks','platform_curriculum_tracks'),('combinations','platform_curriculum_subject_combinations')):
                    await cur.execute('SELECT COUNT(*) FROM '+table+' WHERE template_id=%s',(row[0],)); counts[key]=(await cur.fetchone())[0]
                result.append(_summary(row,counts))
            return result

async def get_template(template_id):
    pool=get_central_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            row=await _template_row(cur,template_id); doc=await _document(cur,template_id); return {**_summary(row,{k:len(v) for k,v in doc.items()}),'document':doc}

async def create_template(payload, actor_id):
    _validate(payload.document); tid=uuid4(); pool=get_central_pool()
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                if payload.is_default: await cur.execute('UPDATE platform_curriculum_templates SET is_default=0 WHERE is_default=1')
                await cur.execute("INSERT INTO platform_curriculum_templates (id,code,name,description,country_code,framework_code,version_no,status,effective_from,effective_to,is_default,created_by,updated_by) VALUES (%s,%s,%s,%s,%s,%s,1,'draft',%s,%s,%s,%s,%s)",(str(tid),payload.code,payload.name,payload.description,payload.country_code,payload.framework_code,payload.effective_from,payload.effective_to,payload.is_default,str(actor_id),str(actor_id)))
                await _replace_document(cur,tid,payload.document)
            await conn.commit()
        except Exception: await conn.rollback(); raise
    return await get_template(tid)

async def update_template(template_id,payload,actor_id):
    pool=get_central_pool()
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                row=await _template_row(cur,template_id)
                if row[7]!='draft': raise HTTPException(409,'Published or archived templates are immutable. Clone the template to create a new version.')
                values=payload.model_dump(exclude_unset=True); doc=values.pop('document',None); sets=[]; params=[]
                for key in ('name','description','country_code','framework_code','effective_from','effective_to'):
                    if key in values: sets.append(key+'=%s'); params.append(values[key])
                if sets: params.extend([str(actor_id),str(template_id)]); await cur.execute('UPDATE platform_curriculum_templates SET '+','.join(sets)+',updated_by=%s WHERE id=%s',tuple(params))
                if doc is not None: await _replace_document(cur,template_id,doc)
            await conn.commit()
        except Exception: await conn.rollback(); raise
    return await get_template(template_id)

async def clone_template(template_id,payload,actor_id):
    source=await get_template(template_id); new_id=uuid4(); code=payload.code or source['code']; name=payload.name or f"{source['name']} v{source['version_no']+1}"; pool=get_central_pool()
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                await cur.execute('SELECT COALESCE(MAX(version_no),0) FROM platform_curriculum_templates WHERE code=%s',(code,)); version=int((await cur.fetchone())[0])+1
                await cur.execute("INSERT INTO platform_curriculum_templates (id,code,name,description,country_code,framework_code,version_no,status,effective_from,effective_to,is_default,created_by,updated_by) VALUES (%s,%s,%s,%s,%s,%s,%s,'draft',%s,%s,0,%s,%s)",(str(new_id),code,name,source['description'],source['country_code'],source['framework_code'],version,source['effective_from'],source['effective_to'],str(actor_id),str(actor_id)))
                await _replace_document(cur,new_id,source['document'])
            await conn.commit()
        except Exception: await conn.rollback(); raise
    return await get_template(new_id)

async def publish_template(template_id,actor_id):
    pool=get_central_pool()
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                row=await _template_row(cur,template_id)
                if row[7]!='draft': raise HTTPException(409,'Only draft curriculum templates can be published')
                doc=await _document(cur,template_id)
                if not doc['levels'] or not doc['grades'] or not doc['subjects']: raise HTTPException(422,'A curriculum template must contain education levels, grades and subjects before publication')
                await cur.execute("UPDATE platform_curriculum_templates SET status='published',updated_by=%s WHERE id=%s",(str(actor_id),str(template_id)))
            await conn.commit()
        except Exception: await conn.rollback(); raise
    return await get_template(template_id)

async def archive_template(template_id,actor_id):
    pool=get_central_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            row=await _template_row(cur,template_id)
            if row[10]: raise HTTPException(409,'Default curriculum template cannot be archived until another default is selected')
            await cur.execute("UPDATE platform_curriculum_templates SET status='archived',updated_by=%s WHERE id=%s",(str(actor_id),str(template_id)))
    return await get_template(template_id)

async def school_curriculum_configuration():
    pool=get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('SELECT id,platform_template_id,template_code,template_version,status,selected_at,allow_local_customization FROM tenant_curriculum_profiles LIMIT 1'); profile=await cur.fetchone()
            await cur.execute('SELECT id,code,name,description,country_code,is_default,is_active FROM curriculum_frameworks ORDER BY is_default DESC,code'); frameworks=await cur.fetchall()
            await cur.execute('SELECT id,framework_id,code,name,effective_from,effective_to,is_active FROM curriculum_versions ORDER BY code'); versions=await cur.fetchall()
            await cur.execute('SELECT code,name,sequence_no FROM education_levels WHERE is_active=1 ORDER BY sequence_no,code'); levels=await cur.fetchall()
            await cur.execute('SELECT code,name,sequence_no FROM grades WHERE is_active=1 ORDER BY sequence_no,code'); grades=await cur.fetchall()
            await cur.execute('SELECT code,name,subject_type,learning_area_id,is_active FROM subjects ORDER BY name'); subjects=await cur.fetchall()
            await cur.execute('SELECT code,name,description,is_active FROM pathways ORDER BY name'); pathways=await cur.fetchall()
            await cur.execute('SELECT t.code,t.name,p.code FROM tracks t JOIN pathways p ON p.id=t.pathway_id ORDER BY p.code,t.code'); tracks=await cur.fetchall()
            await cur.execute('SELECT code,name FROM subject_combinations WHERE is_active=1 ORDER BY name'); combinations=await cur.fetchall()
    return {'profile':None if not profile else {'id':str(profile[0]),'platform_template_id':str(profile[1]),'template_code':profile[2],'template_version':profile[3],'status':profile[4],'selected_at':profile[5],'allow_local_customization':bool(profile[6])},'frameworks':[{'id':str(r[0]),'code':r[1],'name':r[2],'description':r[3],'country_code':r[4],'is_default':bool(r[5]),'is_active':bool(r[6])} for r in frameworks],'versions':[{'id':str(r[0]),'framework_id':str(r[1]),'code':r[2],'name':r[3],'effective_from':r[4],'effective_to':r[5],'is_active':bool(r[6])} for r in versions],'levels':[{'code':r[0],'name':r[1],'sequence_no':r[2]} for r in levels],'grades':[{'code':r[0],'name':r[1],'sequence_no':r[2]} for r in grades],'subjects':[{'code':r[0],'name':r[1],'subject_type':r[2],'learning_area_id':str(r[3]) if r[3] else None,'is_active':bool(r[4])} for r in subjects],'pathways':[{'code':r[0],'name':r[1],'description':r[2],'is_active':bool(r[3])} for r in pathways],'tracks':[{'code':r[0],'name':r[1],'pathway_code':r[2]} for r in tracks],'combinations':[{'code':r[0],'name':r[1]} for r in combinations]}

async def published_template_summaries(): return await list_templates(True)

async def _upsert(cur,table,code,values):
    await cur.execute('SELECT id FROM '+table+' WHERE code=%s LIMIT 1',(code,)); row=await cur.fetchone(); rid=str(row[0]) if row else str(uuid4())
    if row:
        sets=','.join(k+'=%s' for k in values); await cur.execute('UPDATE '+table+' SET '+sets+' WHERE id=%s',tuple(values.values())+(rid,))
    else:
        data={'id':rid,'code':code,**values}; await cur.execute('INSERT INTO '+table+' ('+','.join(data)+') VALUES ('+','.join(['%s']*len(data))+')',tuple(data.values()))
    return rid

async def select_school_template(payload,tenant_id,actor_id):
    central=get_central_pool(); tenant=get_pool()
    async with central.acquire() as conn:
        async with conn.cursor() as cur:
            row=await _template_row(cur,payload.template_id)
            if row[7]!='published': raise HTTPException(409,'Only published curriculum templates can be selected')
            doc=await _document(cur,payload.template_id)
    source=str(payload.template_id)
    async with tenant.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                framework_id=await _upsert(cur,'curriculum_frameworks',row[5],{'tenant_id':str(tenant_id),'name':row[2],'description':row[3],'country_code':row[4],'is_default':1,'platform_source_id':source})
                version_id=await _upsert(cur,'curriculum_versions',f"{row[1]}_v{row[6]}",{'tenant_id':str(tenant_id),'framework_id':framework_id,'name':row[2],'is_active':1,'platform_source_id':source})
                level_ids={}; grade_ids={}; area_ids={}; subject_ids={}; pathway_ids={}; track_ids={}; combo_ids={}
                for x in doc['levels']: level_ids[x['code']]=await _upsert(cur,'education_levels',x['code'],{'tenant_id':str(tenant_id),'curriculum_version_id':version_id,'name':x['name'],'sequence_no':x['sequence_no'],'platform_source_id':source,'is_active':1})
                for x in doc['grades']: grade_ids[x['code']]=await _upsert(cur,'grades',x['code'],{'tenant_id':str(tenant_id),'education_level_id':level_ids[x['education_level_code']],'name':x['name'],'sequence_no':x['sequence_no'],'platform_source_id':source,'is_active':1})
                for x in doc['learning_areas']: area_ids[x['code']]=await _upsert(cur,'learning_areas',x['code'],{'tenant_id':str(tenant_id),'curriculum_version_id':version_id,'name':x['name'],'description':x['description'],'platform_source_id':source,'is_active':1})
                for x in doc['subjects']: subject_ids[x['code']]=await _upsert(cur,'subjects',x['code'],{'tenant_id':str(tenant_id),'name':x['name'],'subject_type':x['subject_type'],'learning_area_id':area_ids.get(x['learning_area_code']),'platform_source_id':source,'is_active':1})
                for x in doc['pathways']: pathway_ids[x['code']]=await _upsert(cur,'pathways',x['code'],{'tenant_id':str(tenant_id),'curriculum_version_id':version_id,'name':x['name'],'description':x['description'],'platform_source_id':source,'is_active':1})
                for x in doc['tracks']:
                    await cur.execute('SELECT id FROM tracks WHERE pathway_id=%s AND code=%s LIMIT 1',(pathway_ids[x['pathway_code']],x['code'])); tr=await cur.fetchone(); track_ids[(x['pathway_code'],x['code'])]=str(tr[0]) if tr else str(uuid4())
                    values={'tenant_id':str(tenant_id),'pathway_id':pathway_ids[x['pathway_code']],'name':x['name'],'description':x['description'],'platform_source_id':source,'is_active':1}
                    if tr: await cur.execute('UPDATE tracks SET name=%s,description=%s,platform_source_id=%s,is_active=1 WHERE id=%s',(x['name'],x['description'],source,track_ids[(x['pathway_code'],x['code'])]))
                    else: await cur.execute('INSERT INTO tracks (id,code,tenant_id,pathway_id,name,description,platform_source_id,is_active) VALUES (%s,%s,%s,%s,%s,%s,%s,1)',(track_ids[(x['pathway_code'],x['code'])],x['code'],str(tenant_id),pathway_ids[x['pathway_code']],x['name'],x['description'],source))
                for x in doc['offerings']:
                    await cur.execute('SELECT id FROM class_levels WHERE code=%s LIMIT 1',(x['grade_code'],)); cl=await cur.fetchone()
                    if cl: await cur.execute("INSERT INTO class_subjects (id,tenant_id,class_level_id,subject_id,is_compulsory,curriculum_version_id,grade_id,requirement_type,weekly_periods,platform_source_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE curriculum_version_id=VALUES(curriculum_version_id),grade_id=VALUES(grade_id),requirement_type=VALUES(requirement_type),weekly_periods=VALUES(weekly_periods),platform_source_id=VALUES(platform_source_id)",(str(uuid4()),str(tenant_id),str(cl[0]),subject_ids[x['subject_code']],1 if x['requirement_type']=='required' else 0,version_id,grade_ids[x['grade_code']],x['requirement_type'],x['weekly_periods'],source))
                for x in doc['combinations']:
                    combo_ids[x['code']]=await _upsert(cur,'subject_combinations',x['code'],{'tenant_id':str(tenant_id),'grade_id':grade_ids.get(x['grade_code']),'pathway_id':pathway_ids.get(x['pathway_code']),'track_id':track_ids.get((x['pathway_code'],x['track_code'])) if x['pathway_code'] and x['track_code'] else None,'name':x['name'],'description':x['description'],'platform_source_id':source,'is_active':1})
                    await cur.execute('DELETE FROM subject_combination_subjects WHERE combination_id=%s AND platform_source_id=%s',(combo_ids[x['code']],source))
                    for i,subject_code in enumerate(x['subjects']): await cur.execute('INSERT INTO subject_combination_subjects (id,tenant_id,combination_id,subject_id,is_required,sort_order,platform_source_id) VALUES (%s,%s,%s,%s,1,%s,%s)',(str(uuid4()),str(tenant_id),combo_ids[x['code']],subject_ids[subject_code],i,source))
                await cur.execute("INSERT INTO tenant_curriculum_profiles (id,tenant_id,platform_template_id,template_code,template_version,status,selected_by,allow_local_customization) VALUES (%s,%s,%s,%s,%s,'active',%s,%s) ON DUPLICATE KEY UPDATE platform_template_id=VALUES(platform_template_id),template_code=VALUES(template_code),template_version=VALUES(template_version),status='active',selected_by=VALUES(selected_by),allow_local_customization=VALUES(allow_local_customization)",(str(uuid4()),str(tenant_id),source,row[1],row[6],str(actor_id),1 if payload.allow_local_customization else 0))
            await conn.commit()
        except Exception: await conn.rollback(); raise
    return await school_curriculum_configuration()
