import hashlib
import json
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.core.database import get_pool


MAX_BATCH_ITEMS = 500


def fingerprint(items) -> str:
    canonical = json.dumps(items, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def receive_batch(tenant_id: UUID, client_batch_id: str, items: list[dict], device_id: UUID | None = None):
    """Persist an offline batch envelope. Individual attendance writes remain governed by the core engine."""
    if not 1 <= len(items) <= MAX_BATCH_ITEMS:
        raise HTTPException(422, f"A sync batch must contain 1-{MAX_BATCH_ITEMS} items")
    client_batch_id = client_batch_id.strip()
    if not 1 <= len(client_batch_id) <= 191:
        raise HTTPException(422, "client_batch_id must contain 1-191 characters")

    pool = get_pool()
    batch_hash = fingerprint(items)
    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT id,request_hash,status,summary_json FROM attendance_sync_batches "
                    "WHERE tenant_id=%s AND client_batch_id=%s FOR UPDATE",
                    (str(tenant_id), client_batch_id),
                )
                existing = await cur.fetchone()
                if existing:
                    if existing[1] != batch_hash:
                        raise HTTPException(409, "client_batch_id was already used with a different batch")
                    await conn.commit()
                    return {"batch_id": existing[0], "status": existing[2], "summary": existing[3]}

                batch_id = uuid4()
                await cur.execute(
                    "INSERT INTO attendance_sync_batches "
                    "(id,tenant_id,device_id,client_batch_id,source,status,request_hash) "
                    "VALUES (%s,%s,%s,%s,'teacher_mobile','received',%s)",
                    (str(batch_id), str(tenant_id), str(device_id) if device_id else None, client_batch_id, batch_hash),
                )
                for item in items:
                    event_id = str(item.get("client_event_id", "")).strip()
                    if not event_id:
                        raise HTTPException(422, "Every sync item requires client_event_id")
                    await cur.execute(
                        "INSERT INTO attendance_sync_items "
                        "(id,tenant_id,batch_id,client_event_id,session_id,student_id) "
                        "VALUES (%s,%s,%s,%s,%s,%s)",
                        (str(uuid4()), str(tenant_id), str(batch_id), event_id,
                         str(item["session_id"]) if item.get("session_id") else None,
                         str(item["student_id"]) if item.get("student_id") else None),
                    )
            await conn.commit()
            return {"batch_id": batch_id, "status": "received", "accepted": 0, "pending": len(items)}
        except Exception:
            await conn.rollback()
            raise
