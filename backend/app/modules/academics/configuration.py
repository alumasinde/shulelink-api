from __future__ import annotations

import json
from uuid import UUID
from app.core.database import get_central_pool, get_pool


def _decode(value, value_type):
    if value == 'null':
        return None
    if value_type == 'integer':
        try: return int(value)
        except (TypeError, ValueError): return value
    if value_type == 'boolean':
        return str(value).lower() in {'1','true','yes','on'}
    if value_type == 'json':
        try: return json.loads(value)
        except (TypeError, ValueError): return value
    return value


async def effective_academic_configuration(tenant_id: UUID):
    central = get_central_pool()
    tenant = get_pool()
    platform_settings = {}
    async with central.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('SELECT setting_key,setting_value,value_type FROM platform_academic_settings WHERE is_active=1 ORDER BY setting_key')
            for key, value, value_type in await cur.fetchall():
                platform_settings[key] = _decode(value, value_type)

    overrides = {}
    async with tenant.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('SELECT setting_key,setting_value,value_type FROM school_settings WHERE tenant_id=%s ORDER BY setting_key', (str(tenant_id),))
            for key, value, value_type in await cur.fetchall():
                overrides[key] = _decode(value, value_type)
            await cur.execute('SELECT category,value_key,label,sort_order FROM academic_reference_values WHERE tenant_id=%s AND is_active=1 ORDER BY category,sort_order,label', (str(tenant_id),))
            reference = {}
            for category, value_key, label, sort_order in await cur.fetchall():
                reference.setdefault(category, []).append({'key': value_key, 'label': label, 'sort_order': sort_order})
            await cur.execute('''SELECT f.code,f.name,v.code,v.name
                FROM curriculum_frameworks f LEFT JOIN curriculum_versions v
                  ON v.framework_id=f.id AND v.tenant_id=f.tenant_id AND v.is_active=1
                WHERE f.tenant_id=%s AND f.is_active=1 ORDER BY f.is_default DESC,f.name,v.effective_from DESC''', (str(tenant_id),))
            curriculum = [{'framework_code': r[0], 'framework_name': r[1], 'version_code': r[2], 'version_name': r[3]} for r in await cur.fetchall()]
            await cur.execute('SELECT code,name,sequence_no FROM education_levels WHERE tenant_id=%s AND is_active=1 ORDER BY sequence_no,name', (str(tenant_id),))
            levels = [{'code': r[0], 'name': r[1], 'sequence': r[2]} for r in await cur.fetchall()]
            await cur.execute('SELECT g.code,g.name,e.code,e.name,g.sequence_no FROM grades g JOIN education_levels e ON e.id=g.education_level_id AND e.tenant_id=g.tenant_id WHERE g.tenant_id=%s AND g.is_active=1 ORDER BY g.sequence_no,g.name', (str(tenant_id),))
            grades = [{'code': r[0], 'name': r[1], 'education_level_code': r[2], 'education_level_name': r[3], 'sequence': r[4]} for r in await cur.fetchall()]

    effective = {**platform_settings, **overrides}
    return {'settings': effective, 'reference_values': reference, 'curriculum': {'frameworks': curriculum, 'education_levels': levels, 'grades': grades}}
