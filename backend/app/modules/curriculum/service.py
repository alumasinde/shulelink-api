from __future__ import annotations

from uuid import UUID, uuid4
from fastapi import HTTPException
from app.core.database import get_central_pool, get_pool
from app.modules.curriculum.schemas import CurriculumTemplateCreate, CurriculumTemplateUpdate, CurriculumTemplateCloneRequest, CurriculumSelectRequest


def _summary(row, counts):
    return {
        'id': UUID(str(row[0])), 'code': row[1], 'name': row[2], 'description': row[3],
        'country_code': row[4], 'framework_code': row[5], 'version_no': int(row[6]),
        'status': row[7], 'effective_from': row[8], 'effective_to': row[9],
        'is_default': bool(row[10]), 'counts': counts,
    }


async def _template_row(cur, template_id: UUID):
    await cur.execute('SELECT id,code,name,description,country_code,framework_code,version_no,status,effective_from,effective_to,is_default FROM platform_curriculum_templates WHERE id=%s', (str(template_id),))
    row = await cur.fetchone()
    if not row:
        raise HTTPException(404, 'Curriculum template not found')
    return row


async def _document(cur, template_id: UUID):
    tid = str(template_id)
    await cur.execute('SELECT id,code,name,sequence_no FROM platform_curriculum_levels WHERE template_id=%s ORDER BY sequence_no,code', (tid,))
    levels = await cur.fetchall()
    level_ids = {str(r[0]): r[1] for r in levels}
    await cur.execute('SELECT id,education_level_id,code,name,sequence_no FROM platform_curriculum_grades WHERE template_id=%s ORDER BY sequence_no,code', (tid,))
    grades = await cur.fetchall()
    await cur.execute('SELECT id,code,name,description,sequence_no FROM platform_curriculum_learning_areas WHERE template_id=%s ORDER BY sequence_no,code', (tid,))
    areas = await cur.fetchall()
    await cur.execute('SELECT id,learning_area_id,code,name,subject_type,description,sequence_no FROM platform_curriculum_subjects WHERE template_id=%s ORDER BY sequence_no,code', (tid,))
    subjects = await cur.fetchall()
    await cur.execute('SELECT grade_id,subject_id,pathway_id,track_id,requirement_type,weekly_periods FROM platform_curriculum_subject_offerings WHERE template_id=%s', (tid,))
    offerings = await cur.fetchall()
    await cur.execute('SELECT id,code,name,description,sequence_no FROM platform_curriculum_pathways WHERE template_id=%s ORDER BY sequence_no,code', (tid,))
    pathways = await cur.fetchall()
    await cur.execute('SELECT pathway_id,code,name,description,sequence_no FROM platform_curriculum_tracks WHERE template_id=%s ORDER BY sequence_no,code', (tid,))
    tracks = await cur.fetchall()
    await cur.execute('SELECT id,grade_id,pathway_id,track_id,code,name,description FROM platform_curriculum_subject_combinations WHERE template_id=%s ORDER BY code', (tid,))
    combinations = await cur.fetchall()
    await cur.execute('SELECT combination_id,subject_id FROM platform_curriculum_combination_subjects WHERE combination_id IN (SELECT id FROM platform_curriculum_subject_combinations WHERE template_id=%s) ORDER BY sort_order,subject_id', (tid,))
    combo_subjects = await cur.fetchall()
    subject_codes = {str(r[0]): r[2] for r in subjects}
    combo_map: dict[str, list[str]] = {}
    for r in combo_subjects:
        combo_map.setdefault(str(r[0]), []).append(subject_codes.get(str(r[1]), str(r[1])))
    pathway_codes = {str(r[0]): r[1] for r in pathways}
    track_codes = {str(r[0]): r[1] for r in tracks}
    grade_codes = {str(r[0]): r[2] for r in grades}
    subject_codes_by_id = {str(r[0]): r[2] for r in subjects}
    return {
        'levels': [{'code': r[1], 'name': r[2], 'sequence_no': r[3]} for r in levels],
        'grades': [{'code': r[2], 'name': r[3], 'education_level_code': level_ids.get(str(r[1]), str(r[1])), 'sequence_no': r[4]} for r in grades],
        'learning_areas': [{'code': r[1], 'name': r[2], 'description': r[3], 'sequence_no': r[4]} for r in areas],
        'subjects': [{'code': r[2], 'name': r[3], 'learning_area_code': next((a[1] for a in areas if str(a[0]) == str(r[1])), None), 'subject_type': r[4], 'description': r[5], 'sequence_no': r[6]} for r in subjects],
        'offerings': [{'grade_code': grade_codes.get(str(r[0]), str(r[0])), 'subject_code': subject_codes_by_id.get(str(r[1]), str(r[1])), 'pathway_code': pathway_codes.get(str(r[2])) if r[2] else None, 'track_code': track_codes.get(str(r[3])) if r[3] else None, 'requirement_type': r[4], 'weekly_periods': float(r[5]) if r[5] is not None else None} for r in offerings],
        'pathways': [{'code': r[1], 'name': r[2], 'description': r[3], 'sequence_no': r[4]} for r in pathways],
        'tracks': [{'pathway_code': pathway_codes.get(str(r[0]), str(r[0])), 'code': r[1], 'name': r[2], 'description': r[3], 'sequence_no': r[4]} for r in tracks],
        'combinations': [{'code': r[4], 'name': r[5], 'grade_code': grade_codes.get(str(r[1])) if r[1] else None, 'pathway_code': pathway_codes.get(str(r[2])) if r[2] else None, 'track_code': track_codes.get(str(r[3])) if r[3] else None, 'description': r[6], 'subjects': combo_map.get(str(r[0]), [])} for r in combinations],
    }


def _validate_document(doc):
    def unique(items, field='code'):
        vals = [getattr(x, field) for x in items]
        if len(vals) != len(set(vals)):
            raise HTTPException(422, f'Duplicate {field} in curriculum template')
    unique(doc.levels); unique(doc.grades); unique(doc.learning_areas); unique(doc.subjects); unique(doc.pathways); unique(doc.combinations)
    level_codes = {x.code for x in doc.levels}; grade_codes = {x.code for x in doc.grades}; area_codes = {x.code for x in doc.learning_areas}; subject_codes = {x.code for x in doc.subjects}; pathway_codes = {x.code for x in doc.pathways}
    if any(x.education_level_code not in level_codes for x in doc.grades): raise HTTPException(422, 'Every grade must reference an existing education level')
    if any(x.learning_area_code and x.learning_area_code not in area_codes for x in doc.subjects): raise HTTPException(422, 'Every subject learning area must exist')
    track_keys = {(x.pathway_code, x.code) for x in doc.tracks}
    if any(x.pathway_code not in pathway_codes for x in doc.tracks): raise HTTPException(422, 'Every track must reference an existing pathway')
    for x in doc.offerings:
        if x.grade_code not in grade_codes or x.subject_code not in subject_codes: raise HTTPException(422, 'Curriculum offering references an unknown grade or subject')
        if x.pathway_code and x.pathway_code not in pathway_codes: raise HTTPException(422, 'Curriculum offering references an unknown pathway')
        if x.track_code and (x.pathway_code, x.track_code) not in track_keys: raise HTTPException(422, 'Curriculum offering references an unknown track')
    for x in doc.combinations:
        if x.grade_code and x.grade_code not in grade_codes: raise HTTPException(422, 'Subject combination references an unknown grade')
        if x.pathway_code and x.pathway_code not in pathway_codes: raise HTTPException(422, 'Subject combination references an unknown pathway')
        if x.track_code and (x.pathway_code, x.track_code) not in track_keys: raise HTTPException(422, 'Subject combination references an unknown track')
        if any(code not in subject_codes for code in x.subjects): raise HTTPException(422, 'Subject combination contains an unknown subject')


async def _replace_document(cur, template_id: UUID, doc):
    _validate_document(doc)
    tid = str(template_id)
    await cur.execute('DELETE FROM platform_curriculum_subject_offerings WHERE template_id=%s', (tid,))
    await cur.execute('DELETE FROM platform_curriculum_combination_subjects WHERE combination_id IN (SELECT id FROM platform_curriculum_subject_combinations WHERE template_id=%s)', (tid,))
    await cur.execute('DELETE FROM platform_curriculum_subject_combinations WHERE template_id=%s', (tid,))
    await cur.execute('DELETE FROM platform_curriculum_subjects WHERE template_id=%s', (tid,))
    await cur.execute('DELETE FROM platform_curriculum_learning_areas WHERE template_id=%s', (tid,))
    await cur.execute('DELETE FROM platform_curriculum_tracks WHERE template_id=%s', (tid,))
    await cur.execute('DELETE FROM platform_curriculum_pathways WHERE template_id=%s', (tid,))
    await cur.execute('DELETE FROM platform_curriculum_grades WHERE template_id=%s', (tid,))
    await cur.execute('DELETE FROM platform_curriculum_levels WHERE template_id=%s', (tid,))
    level_ids={x.code:str(uuid4()) for x in doc.levels}; grade_ids={x.code:str(uuid4()) for x in doc.grades}; area_ids={x.code:str(uuid4()) for x in doc.learning_areas}; subject_ids={x.code:str(uuid4()) for x in doc.subjects}; pathway_ids={x.code:str(uuid4()) for x in doc.pathways}; track_ids={(x.pathway_code,x.code):str(uuid4()) for x in doc.tracks}; combo_ids={x.code:str(uuid4()) for x in doc.combinations}
    for x in doc.levels: await cur.execute('INSERT INTO platform_curriculum_levels (id,template_id,code,name,sequence_no) VALUES (%s,%s,%s,%s,%s)', (level_ids[x.code],tid,x.code,x.name,x.sequence_no))
    for x in doc.grades: await cur.execute('INSERT INTO platform_curriculum_grades (id,template_id,education_level_id,code,name,sequence_no) VALUES (%s,%s,%s,%s,%s,%s)', (grade_ids[x.code],tid,level_ids[x.education_level_code],x.code,x.name,x.sequence_no))
    for x in doc.learning_areas: await cur.execute('INSERT INTO platform_curriculum_learning_areas (id,template_id,code,name,description,sequence_no) VALUES (%s,%s,%s,%s,%s,%s)', (area_ids[x.code],tid,x.code,x.name,x.description,x.sequence_no))
    for x in doc.subjects: await cur.execute('INSERT INTO platform_curriculum_subjects (id,template_id,learning_area_id,code,name,subject_type,description,sequence_no) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)', (subject_ids[x.code],tid,area_ids.get(x.learning_area_code) if x.learning_area_code else None,x.code,x.name,x.subject_type,x.description,x.sequence_no))
    for x in doc.pathways: await cur.execute('INSERT INTO platform_curriculum_pathways (id,template_id,code,name,description,sequence_no) VALUES (%s,%s,%s,%s,%s,%s)', (pathway_ids[x.code],tid,x.code,x.name,x.description,x.sequence_no))
    for x in doc.tracks: await cur.execute('INSERT INTO platform_curriculum_tracks (id,template_id,pathway_id,code,name,description,sequence_no) VALUES (%s,%s,%s,%s,%s,%s,%s)', (track_ids[(x.pathway_code,x.code)],tid,pathway_ids[x.pathway_code],x.code,x.name,x.description,x.sequence_no))
    for x in doc.offerings: await cur.execute('INSERT INTO platform_curriculum_subject_offerings (id,template_id,grade_id,subject_id,pathway_id,track_id,requirement_type,weekly_periods) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)', (str(uuid4()),tid,grade_ids[x.grade_code],subject_ids[x.subject_code],pathway_ids.get(x.pathway_code) if x.pathway_code else None,track_ids.get((x.pathway_code,x.track_code)) if x.pathway_code and x.track_code else None,x.requirement_type,x.weekly_periods))
    for x in doc.combinations: await cur.execute('INSERT INTO platform_curriculum_subject_combinations (id,template_id,grade_id,pathway_id,track_id,code,name,description) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)', (combo_ids[x.code],tid,grade_ids.get(x.grade_code) if x.grade_code else None,pathway_ids.get(x.pathway_code) if x.pathway_code else None,track_ids.get((x.pathway_code,x.track_code)) if x.pathway_code and x.track_code else None,x.code,x.name,x.description)); [await cur.execute('INSERT INTO platform_curriculum_combination_subjects (id,combination_id,subject_id,is_required,sort_order) VALUES (%s,%s,%s,1,%s)', (str(uuid4()),combo_ids[x.code],subject_ids[s],i)) for i,s in enumerate(x.subjects)]


async def list_templates(published_only=False):
    pool=get_central_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            sql='SELECT id,code,name,description,country_code,framework_code,version_no,status,effective_from,effective_to,is_default FROM platform_curriculum_templates'
            if published_only: sql += " WHERE status='published'"
            sql += ' ORDER BY is_default DESC,name,version_no DESC'
            await cur.execute(sql); rows=await cur.fetchall(); result=[]
            for row in rows:
                await cur.execute('SELECT COUNT(*) FROM platform_curriculum_levels WHERE template_id=%s',(row[0],)); levels=(await cur.fetchone())[0]
                await cur.execute('SELECT COUNT(*) FROM platform_curriculum_grades WHERE template_id=%s',(row[0],)); grades=(await cur.fetchone())[0]
                await cur.execute('SELECT COUNT(*) FROM platform_curriculum_subjects WHERE template_id=%s',(row[0],)); subjects=(await cur.fetchone())[0]
                await cur.execute('SELECT COUNT(*) FROM platform_curriculum_pathways WHERE template_id=%s',(row[0],)); pathways=(await cur.fetchone())[0]
                await cur.execute('SELECT COUNT(*) FROM platform_curriculum_tracks WHERE template_id=%s',(row[0],)); tracks=(await cur.fetchone())[0]
                await cur.execute('SELECT COUNT(*) FROM platform_curriculum_subject_combinations WHERE template_id=%s',(row[0],)); combinations=(await cur.fetchone())[0]
                result.append(_summary(row,{'levels':levels,'grades':grades,'subjects':subjects,'pathways':pathways,'tracks':tracks,'combinations':combinations}))
            return result


async def get_template(template_id: UUID):
    pool=get_central_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            row=await _template_row(cur,template_id); doc=await _document(cur,template_id)
            counts={k:len(v) for k,v in doc.items()}; return {**_summary(row,counts),'document':doc}


async def create_template(payload: CurriculumTemplateCreate, actor_id: UUID):
    pool=get_central_pool(); tid=uuid4(); doc=payload.document
    _validate_document(doc)
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                if payload.is_default: await cur.execute("UPDATE platform_curriculum_templates SET is_default=0 WHERE is_default=1")
                await cur.execute('INSERT INTO platform_curriculum_templates (id,code,name,description,country_code,framework_code,version_no,status,effective_from,effective_to,is_default,created_by,updated_by) VALUES (%s,%s,%s,%s,%s,%s,1,\'draft\',%s,%s,%s,%s,%s)',(str(tid),payload.code,payload.name,payload.description,payload.country_code,payload.framework_code,payload.effective_from,payload.effective_to,payload.is_default,str(actor_id),str(actor_id)))
                await _replace_document(cur,tid,doc)
            await conn.commit()
        except Exception: await conn.rollback(); raise
    return await get_template(tid)


async def update_template(template_id: UUID, payload: CurriculumTemplateUpdate, actor_id: UUID):
    pool=get_central_pool()
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                row=await _template_row(cur,template_id)
                if row[7] != 'draft': raise HTTPException(409,'Published or archived templates are immutable. Clone the template to create a new version.')
                values=payload.model_dump(exclude_unset=True); doc=values.pop('document',None)
                if values:
                    sets=[]; params=[]
                    for key in ('name','description','country_code','framework_code','effective_from','effective_to'):
                        if key in values: sets.append(f'{key}=%s'); params.append(values[key])
                    if sets: params.extend([str(actor_id),str(template_id)]); await cur.execute(f'UPDATE platform_curriculum_templates SET {",".join(sets)},updated_by=%s WHERE id=%s',tuple(params))
                if doc is not None: await _replace_document(cur,template_id,doc)
            await conn.commit()
        except Exception: await conn.rollback(); raise
    return await get_template(template_id)


async def clone_template(template_id: UUID, payload: CurriculumTemplateCloneRequest, actor_id: UUID):
    source=await get_template(template_id); pool=get_central_pool(); new_id=uuid4(); code=payload.code or source['code']; name=payload.name or f"{source['name']} v{source['version_no']+1}"
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                await cur.execute('SELECT COALESCE(MAX(version_no),0) FROM platform_curriculum_templates WHERE code=%s',(code,)); version=int((await cur.fetchone())[0])+1
                await cur.execute('INSERT INTO platform_curriculum_templates (id,code,name,description,country_code,framework_code,version_no,status,effective_from,effective_to,is_default,created_by,updated_by) VALUES (%s,%s,%s,%s,%s,%s,%s,\'draft\',%s,%s,0,%s,%s)',(str(new_id),code,name,source['description'],source['country_code'],source['framework_code'],version,source['effective_from'],source['effective_to'],str(actor_id),str(actor_id)))
                await _replace_document(cur,new_id,source['document'])
            await conn.commit()
        except Exception: await conn.rollback(); raise
    return await get_template(new_id)


async def publish_template(template_id: UUID, actor_id: UUID):
    pool=get_central_pool()
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                row=await _template_row(cur,template_id)
                if row[7] != 'draft': raise HTTPException(409,'Only draft curriculum templates can be published')
                doc=await _document(cur,template_id)
                if not doc['levels'] or not doc['grades'] or not doc['subjects']: raise HTTPException(422,'A curriculum template must contain education levels, grades and subjects before publication')
                await cur.execute('UPDATE platform_curriculum_templates SET status=\'published\',updated_by=%s WHERE id=%s',(str(actor_id),str(template_id)))
            await conn.commit()
        except Exception: await conn.rollback(); raise
    return await get_template(template_id)


async def archive_template(template_id: UUID, actor_id: UUID):
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
            await cur.execute('SELECT id,platform_template_id,template_code,template_version,status,selected_at,allow_local_customization FROM tenant_curriculum_profiles LIMIT 1')
            profile=await cur.fetchone()
            await cur.execute('SELECT id,code,name,description,country_code,framework_code,version_no,status,effective_from,effective_to,is_default FROM curriculum_frameworks f JOIN (SELECT 1) x ON 1=1 ORDER BY is_default DESC,code')
            frameworks=await cur.fetchall()
            await cur.execute('SELECT code,name,sequence_no FROM education_levels ORDER BY sequence_no,code'); levels=await cur.fetchall()
            await cur.execute('SELECT code,name,sequence_no FROM grades ORDER BY sequence_no,code'); grades=await cur.fetchall()
            await cur.execute('SELECT code,name,subject_type,learning_area_id,is_active FROM subjects ORDER BY name'); subjects=await cur.fetchall()
            await cur.execute('SELECT code,name,description,is_active FROM pathways ORDER BY name'); pathways=await cur.fetchall()
            await cur.execute('SELECT t.code,t.name,p.code FROM tracks t JOIN pathways p ON p.id=t.pathway_id ORDER BY p.sequence_no,t.sequence_no'); tracks=await cur.fetchall()
            await cur.execute('SELECT code,name FROM subject_combinations WHERE is_active=1 ORDER BY name'); combinations=await cur.fetchall()
    return {'profile': None if not profile else {'id':str(profile[0]),'platform_template_id':str(profile[1]),'template_code':profile[2],'template_version':profile[3],'status':profile[4],'selected_at':profile[5],'allow_local_customization':bool(profile[6])},'frameworks':[{'id':str(r[0]),'code':r[1],'name':r[2],'description':r[3],'country_code':r[4],'framework_code':r[5],'version_no':r[6],'status':r[7],'effective_from':r[8],'effective_to':r[9],'is_default':bool(r[10])} for r in frameworks],'levels':[{'code':r[0],'name':r[1],'sequence_no':r[2]} for r in levels],'grades':[{'code':r[0],'name':r[1],'sequence_no':r[2]} for r in grades],'subjects':[{'code':r[0],'name':r[1],'subject_type':r[2],'learning_area_id':str(r[3]) if r[3] else None,'is_active':bool(r[4])} for r in subjects],'pathways':[{'code':r[0],'name':r[1],'description':r[2],'is_active':bool(r[3])} for r in pathways],'tracks':[{'code':r[0],'name':r[1],'pathway_code':r[2]} for r in tracks],'combinations':[{'code':r[0],'name':r[1]} for r in combinations]}


async def published_template_summaries(): return await list_templates(True)


async def select_school_template(payload: CurriculumSelectRequest, tenant_id: UUID, actor_id: UUID):
    central=get_central_pool(); tenant=get_pool(); template_id=str(payload.template_id)
    async with central.acquire() as conn:
        async with conn.cursor() as cur:
            row=await _template_row(cur,payload.template_id)
            if row[7] != 'published': raise HTTPException(409,'Only published curriculum templates can be selected')
            doc=await _document(cur,payload.template_id)
    async with tenant.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                # Framework/version are the tenant-local academic identity of the selected template.
                await cur.execute('SELECT id FROM curriculum_frameworks WHERE code=%s LIMIT 1',(row[5],)); framework=await cur.fetchone(); framework_id=str(framework[0]) if framework else str(uuid4())
                if framework: await cur.execute('UPDATE curriculum_frameworks SET name=%s,description=%s,country_code=%s,is_default=1,platform_source_id=%s WHERE id=%s',(row[2],row[3],row[4],template_id,framework_id))
                else: await cur.execute('INSERT INTO curriculum_frameworks (id,tenant_id,code,name,description,country_code,is_default,platform_source_id) VALUES (%s,%s,%s,%s,%s,%s,1,%s)',(framework_id,str(tenant_id),row[5],row[2],row[3],row[4],template_id))
                await cur.execute('SELECT id FROM curriculum_versions WHERE framework_id=%s AND code=%s LIMIT 1',(framework_id,f"{row[1]}_v{row[6]}")); version=await cur.fetchone(); version_id=str(version[0]) if version else str(uuid4())
                if version: await cur.execute('UPDATE curriculum_versions SET name=%s,is_active=1,platform_source_id=%s WHERE id=%s',(row[2],template_id,version_id))
                else: await cur.execute('INSERT INTO curriculum_versions (id,tenant_id,framework_id,code,name,is_active,platform_source_id) VALUES (%s,%s,%s,%s,%s,1,%s)',(version_id,str(tenant_id),framework_id,f"{row[1]}_v{row[6]}",row[2],template_id))
                level_ids={}; grade_ids={}; area_ids={}; subject_ids={}; pathway_ids={}; track_ids={}; combo_ids={}
                for x in doc['levels']:
                    await cur.execute('SELECT id FROM education_levels WHERE code=%s LIMIT 1',(x['code'],)); r=await cur.fetchone(); lid=str(r[0]) if r else str(uuid4()); level_ids[x['code']]=lid
                    if r: await cur.execute('UPDATE education_levels SET name=%s,sequence_no=%s,curriculum_version_id=%s,platform_source_id=%s,is_active=1 WHERE id=%s',(x['name'],x['sequence_no'],version_id,None,lid))
                    else: await cur.execute('INSERT INTO education_levels (id,tenant_id,curriculum_version_id,code,name,sequence_no,platform_source_id) VALUES (%s,%s,%s,%s,%s,%s,%s)',(lid,str(tenant_id),version_id,x['code'],x['name'],x['sequence_no'],None))
                for x in doc['grades']:
                    await cur.execute('SELECT id FROM grades WHERE code=%s LIMIT 1',(x['code'],)); r=await cur.fetchone(); gid=str(r[0]) if r else str(uuid4()); grade_ids[x['code']]=gid
                    if r: await cur.execute('UPDATE grades SET name=%s,sequence_no=%s,education_level_id=%s,platform_source_id=%s WHERE id=%s',(x['name'],x['sequence_no'],level_ids[x['education_level_code']],None,gid))
                    else: await cur.execute('INSERT INTO grades (id,tenant_id,education_level_id,code,name,sequence_no,platform_source_id) VALUES (%s,%s,%s,%s,%s,%s,%s)',(gid,str(tenant_id),level_ids[x['education_level_code']],x['code'],x['name'],x['sequence_no'],None))
                for x in doc['learning_areas']:
                    await cur.execute('SELECT id FROM learning_areas WHERE code=%s LIMIT 1',(x['code'],)); r=await cur.fetchone(); aid=str(r[0]) if r else str(uuid4()); area_ids[x['code']]=aid
                    if r: await cur.execute('UPDATE learning_areas SET name=%s,description=%s,curriculum_version_id=%s,platform_source_id=%s,is_active=1 WHERE id=%s',(x['name'],x['description'],version_id,None,aid))
                    else: await cur.execute('INSERT INTO learning_areas (id,tenant_id,curriculum_version_id,code,name,description,platform_source_id) VALUES (%s,%s,%s,%s,%s,%s,%s)',(aid,str(tenant_id),version_id,x['code'],x['name'],x['description'],None))
                for x in doc['subjects']:
                    await cur.execute('SELECT id FROM subjects WHERE code=%s LIMIT 1',(x['code'],)); r=await cur.fetchone(); sid=str(r[0]) if r else str(uuid4()); subject_ids[x['code']]=sid
                    if r: await cur.execute('UPDATE subjects SET name=%s,subject_type=%s,learning_area_id=%s,platform_source_id=%s,is_active=1 WHERE id=%s',(x['name'],x['subject_type'],area_ids.get(x['learning_area_code']) if x['learning_area_code'] else None,None,sid))
                    else: await cur.execute('INSERT INTO subjects (id,tenant_id,code,name,subject_type,learning_area_id,platform_source_id) VALUES (%s,%s,%s,%s,%s,%s,%s)',(sid,str(tenant_id),x['code'],x['name'],x['subject_type'],area_ids.get(x['learning_area_code']) if x['learning_area_code'] else None,None))
                for x in doc['pathways']:
                    await cur.execute('SELECT id FROM pathways WHERE code=%s LIMIT 1',(x['code'],)); r=await cur.fetchone(); pid=str(r[0]) if r else str(uuid4()); pathway_ids[x['code']]=pid
                    if r: await cur.execute('UPDATE pathways SET name=%s,description=%s,curriculum_version_id=%s,platform_source_id=%s,is_active=1 WHERE id=%s',(x['name'],x['description'],version_id,None,pid))
                    else: await cur.execute('INSERT INTO pathways (id,tenant_id,curriculum_version_id,code,name,description,platform_source_id) VALUES (%s,%s,%s,%s,%s,%s,%s)',(pid,str(tenant_id),version_id,x['code'],x['name'],x['description'],None))
                for x in doc['tracks']:
                    await cur.execute('SELECT id FROM tracks WHERE pathway_id=%s AND code=%s LIMIT 1',(pathway_ids[x['pathway_code']],x['code'])); r=await cur.fetchone(); tr=str(r[0]) if r else str(uuid4()); track_ids[(x['pathway_code'],x['code'])]=tr
                    if r: await cur.execute('UPDATE tracks SET name=%s,description=%s,platform_source_id=%s,is_active=1 WHERE id=%s',(x['name'],x['description'],None,tr))
                    else: await cur.execute('INSERT INTO tracks (id,tenant_id,pathway_id,code,name,description,platform_source_id) VALUES (%s,%s,%s,%s,%s,%s,%s)',(tr,str(tenant_id),pathway_ids[x['pathway_code']],x['code'],x['name'],x['description'],None))
                for x in doc['offerings']:
                    await cur.execute('SELECT id FROM class_levels WHERE code=%s LIMIT 1',(x['grade_code'],)); cl=await cur.fetchone()
                    if cl:
                        await cur.execute('INSERT INTO class_subjects (id,tenant_id,class_level_id,subject_id,is_compulsory,curriculum_version_id,grade_id,requirement_type,weekly_periods,platform_source_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE curriculum_version_id=VALUES(curriculum_version_id),grade_id=VALUES(grade_id),requirement_type=VALUES(requirement_type),weekly_periods=VALUES(weekly_periods),platform_source_id=VALUES(platform_source_id)',(str(uuid4()),str(tenant_id),str(cl[0]),subject_ids[x['subject_code']],1 if x['requirement_type']=='required' else 0,version_id,grade_ids[x['grade_code']],x['requirement_type'],x['weekly_periods'],None))
                for x in doc['combinations']:
                    await cur.execute('SELECT id FROM subject_combinations WHERE code=%s LIMIT 1',(x['code'],)); r=await cur.fetchone(); cid=str(r[0]) if r else str(uuid4()); combo_ids[x['code']]=cid
                    if r: await cur.execute('UPDATE subject_combinations SET name=%s,description=%s,grade_id=%s,pathway_id=%s,track_id=%s,platform_source_id=%s,is_active=1 WHERE id=%s',(x['name'],x['description'],grade_ids.get(x['grade_code']) if x['grade_code'] else None,pathway_ids.get(x['pathway_code']) if x['pathway_code'] else None,track_ids.get((x['pathway_code'],x['track_code'])) if x['pathway_code'] and x['track_code'] else None,None,cid))
                    else: await cur.execute('INSERT INTO subject_combinations (id,tenant_id,grade_id,pathway_id,track_id,code,name,description,platform_source_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)',(cid,str(tenant_id),grade_ids.get(x['grade_code']) if x['grade_code'] else None,pathway_ids.get(x['pathway_code']) if x['pathway_code'] else None,track_ids.get((x['pathway_code'],x['track_code'])) if x['pathway_code'] and x['track_code'] else None,x['code'],x['name'],x['description'],None))
                    await cur.execute('DELETE FROM subject_combination_subjects WHERE combination_id=%s AND platform_source_id IS NOT NULL',(cid,))
                    for i,code in enumerate(x['subjects']): await cur.execute('INSERT IGNORE INTO subject_combination_subjects (id,tenant_id,combination_id,subject_id,is_required,sort_order,platform_source_id) VALUES (%s,%s,%s,%s,1,%s,%s)',(str(uuid4()),str(tenant_id),cid,subject_ids[code],i,None))
                await cur.execute('INSERT INTO tenant_curriculum_profiles (id,tenant_id,platform_template_id,template_code,template_version,status,selected_by,allow_local_customization) VALUES (%s,%s,%s,%s,%s,\'active\',%s,%s) ON DUPLICATE KEY UPDATE platform_template_id=VALUES(platform_template_id),template_code=VALUES(template_code),template_version=VALUES(template_version),status=\'active\',selected_by=VALUES(selected_by),allow_local_customization=VALUES(allow_local_customization)',(str(uuid4()),str(tenant_id),template_id,row[1],row[6],str(actor_id),1 if payload.allow_local_customization else 0))
            await conn.commit()
        except Exception: await conn.rollback(); raise
    return await school_curriculum_configuration()
