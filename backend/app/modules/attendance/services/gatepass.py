from uuid import UUID


async def sync_gatepass_exemption(tenant_id: UUID, student_id: UUID, gatepass_id: UUID, starts_at, ends_at, created_by_user_id: UUID | None = None):
    """Integration boundary for a gate-pass module.

    The gate-pass domain owns approval and QR validation. Attendance only receives
    the approved time window as an exemption, keeping both domains independent.
    """
    from app.core.database import get_pool

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO attendance_exemptions "
                "(id,tenant_id,student_id,exemption_type,status,starts_at,ends_at,source_type,source_id,created_by_user_id) "
                "VALUES (UUID(),%s,%s,'leave','approved',%s,%s,'gatepass',%s,%s)",
                (str(tenant_id), str(student_id), starts_at, ends_at, str(gatepass_id), str(created_by_user_id) if created_by_user_id else None),
            )
    return {"student_id": student_id, "gatepass_id": gatepass_id, "status": "approved"}
