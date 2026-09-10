from __future__ import annotations

import json
from uuid import UUID, uuid4
from fastapi import HTTPException
from app.core.database import get_central_pool


def decode(value, value_type):
    if value == 'null': return None
    if value_type == 'integer':
        try: return int(value)
        except (TypeError, ValueError): return value
    if value_type == 'boolean': return str(value).lower() in {'1','true','yes','on'}
    if value_type == 'json':
        try: return json.loads(value)
        except (TypeError, ValueError): return value
    return value


def encode(value, value_type):
    if value_type == 'json': return json.dumps(value, separators=(',', ':'))
    if value_type == 'boolean': return 'true' if bool(value) else 'false'
    if value is None: return 'null'
    return str(value)


async def list_platform_academic_settings():
    pool = get_central_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('SELECT id,setting_key,setting_value,value_type,description,is_active,updated_at FROM platform_academic_settings ORDER BY setting_key')
            rows = await cur.fetchall()
    return [{'id': str(r[0]), 'setting_key': r[1], 'setting_value': decode(r[2], r[3]), 'value_type': r[3], 'description': r[4], 'is_active': bool(r[5]), 'updated_at': r[6]} for r in rows]


async def update_platform_academic_setting(setting_id: UUID, payload: dict, actor_id: UUID):
    pool = get_central_pool()
    value_type = payload.get('value_type')
    if value_type not in {'string','integer','boolean','json'}:
        raise HTTPException(422, 'value_type must be string, integer, boolean or json')
    encoded = encode(payload.get('setting_value'), value_type)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute('SELECT setting_key FROM platform_academic_settings WHERE id=%s', (str(setting_id),))
            row = await cur.fetchone()
            if not row: raise HTTPException(404, 'Academic platform setting not found')
            await cur.execute('UPDATE platform_academic_settings SET setting_value=%s,value_type=%s,updated_by=%s WHERE id=%s', (encoded,value_type,str(actor_id),str(setting_id)))
            await cur.execute('SELECT id,setting_key,setting_value,value_type,description,is_active,updated_at FROM platform_academic_settings WHERE id=%s', (str(setting_id),))
            r = await cur.fetchone()
    return {'id':str(r[0]),'setting_key':r[1],'setting_value':decode(r[2],r[3]),'value_type':r[3],'description':r[4],'is_active':bool(r[5]),'updated_at':r[6]}
