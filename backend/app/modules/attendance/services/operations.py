from datetime import date

from fastapi import HTTPException

from app.core.database import get_central_pool, get_pool


def sid(value):
    return str(value) if value is not None else None


def rate(numerator, denominator):
    return round((numerator / denominator) * 100, 2) if denominator else 0.0


async def has_permission(tenant_id, user_id, permission_code):
    pool = get_central_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT 1 FROM tenant_memberships m JOIN tenant_membership_roles mr ON mr.membership_id=m.id "
                "JOIN tenant_roles r ON r.id=mr.role_id JOIN tenant_role_permissions rp ON rp.role_id=r.id "
                "JOIN tenant_permissions p ON p.id=rp.permission_id WHERE m.tenant_id=%s AND m.tenant_user_id=%s "
                "AND m.status='active' AND p.code=%s LIMIT 1",
                (sid(tenant_id), sid(user_id), permission_code),
            )
            return await cur.fetchone() is not None


async def list_sessions(tenant_id, attendance_date=None, session_type=None, status=None, class_level_id=None, stream_id=None, limit=100):
    limit = min(max(int(limit), 1), 200)
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            sql = (
                "SELECT s.id,s.session_date,s.session_type,s.class_level_id,s.stream_id,s.status,s.scheduled_start_at,s.scheduled_end_at,"
                "COUNT(DISTINCT e.student_id),COUNT(DISTINCT ar.student_id),"
                "COUNT(DISTINCT CASE WHEN a.code IN ('present','late','half_day') THEN ar.student_id END),"
                "COUNT(DISTINCT CASE WHEN a.code='excused' THEN ar.student_id END),"
                "COUNT(DISTINCT CASE WHEN a.code='on_leave' THEN ar.student_id END) "
                "FROM attendance_sessions s "
                "LEFT JOIN student_enrollments e ON e.tenant_id=s.tenant_id AND e.class_level_id=s.class_level_id AND (e.stream_id <=> s.stream_id) "
                "AND e.enrollment_date<=s.session_date AND (e.exit_date IS NULL OR e.exit_date>=s.session_date) AND e.status='active' "
                "LEFT JOIN attendance_records ar ON ar.tenant_id=s.tenant_id AND ar.session_id=s.id AND ar.student_id=e.student_id "
                "LEFT JOIN attendance_statuses a ON a.id=ar.attendance_status_id AND a.tenant_id=ar.tenant_id WHERE s.tenant_id=%s"
            )
            params = [sid(tenant_id)]
            if attendance_date: sql += " AND s.session_date=%s"; params.append(attendance_date)
            if session_type: sql += " AND s.session_type=%s"; params.append(session_type)
            if status: sql += " AND s.status=%s"; params.append(status)
            if class_level_id: sql += " AND s.class_level_id=%s"; params.append(sid(class_level_id))
            if stream_id: sql += " AND s.stream_id=%s"; params.append(sid(stream_id))
            sql += " GROUP BY s.id ORDER BY s.session_date DESC,s.scheduled_start_at,s.created_at DESC LIMIT %s"; params.append(limit)
            await cur.execute(sql, params); rows = await cur.fetchall()
    result=[]
    for row in rows:
        roster_count, marked_count = int(row[8] or 0), int(row[9] or 0)
        attended, excused, on_leave = int(row[10] or 0), int(row[11] or 0), int(row[12] or 0)
        eligible=max(roster_count-excused-on_leave,0)
        result.append({"id":row[0],"session_date":row[1],"session_type":row[2],"class_level_id":row[3],"stream_id":row[4],"status":row[5],"scheduled_start_at":row[6],"scheduled_end_at":row[7],"roster_count":roster_count,"marked_count":marked_count,"not_marked_count":max(roster_count-marked_count,0),"attendance_rate":rate(attended,eligible)})
    return result


async def session_completion(tenant_id, session_id):
    pool=get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id,status FROM attendance_sessions WHERE id=%s AND tenant_id=%s",(sid(session_id),sid(tenant_id)))
            session=await cur.fetchone()
            if not session: raise HTTPException(404,"Attendance session not found")
            await cur.execute(
                "SELECT COUNT(DISTINCT e.student_id),COUNT(DISTINCT ar.student_id),"
                "COUNT(DISTINCT CASE WHEN a.code IN ('present','late','half_day') THEN ar.student_id END),"
                "COUNT(DISTINCT CASE WHEN a.code='excused' THEN ar.student_id END),COUNT(DISTINCT CASE WHEN a.code='on_leave' THEN ar.student_id END) "
                "FROM attendance_sessions s JOIN student_enrollments e ON e.tenant_id=s.tenant_id AND e.class_level_id=s.class_level_id AND (e.stream_id <=> s.stream_id) "
                "AND e.enrollment_date<=s.session_date AND (e.exit_date IS NULL OR e.exit_date>=s.session_date) AND e.status='active' "
                "LEFT JOIN attendance_records ar ON ar.tenant_id=s.tenant_id AND ar.session_id=s.id AND ar.student_id=e.student_id "
                "LEFT JOIN attendance_statuses a ON a.id=ar.attendance_status_id AND a.tenant_id=ar.tenant_id WHERE s.id=%s AND s.tenant_id=%s",
                (sid(session_id),sid(tenant_id)))
            row=await cur.fetchone()
    roster_count=int(row[0] or 0); marked_count=int(row[1] or 0); attended=int(row[2] or 0); excused=int(row[3] or 0); on_leave=int(row[4] or 0)
    not_marked=max(roster_count-marked_count,0); eligible=max(roster_count-excused-on_leave,0)
    return {"session_id":session[0],"status":session[1],"roster_count":roster_count,"marked_count":marked_count,"not_marked_count":not_marked,"completion_rate":rate(marked_count,roster_count),"attendance_rate":rate(attended,eligible),"can_close":not_marked==0,"requires_override":not_marked>0}


async def dashboard(tenant_id, attendance_date):
    pool=get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*),SUM(status='open'),SUM(status='closed') FROM attendance_sessions WHERE tenant_id=%s AND session_date=%s",(sid(tenant_id),attendance_date)); sessions,open_sessions,closed_sessions=await cur.fetchone()
            await cur.execute(
                "SELECT COUNT(DISTINCT e.student_id),COUNT(DISTINCT ar.student_id),SUM(a.code='present'),SUM(a.code='absent'),SUM(a.code='late'),SUM(a.code='excused'),SUM(a.code='on_leave') "
                "FROM attendance_sessions s JOIN student_enrollments e ON e.tenant_id=s.tenant_id AND e.class_level_id=s.class_level_id AND (e.stream_id <=> s.stream_id) "
                "AND e.enrollment_date<=s.session_date AND (e.exit_date IS NULL OR e.exit_date>=s.session_date) AND e.status='active' "
                "LEFT JOIN attendance_records ar ON ar.tenant_id=s.tenant_id AND ar.session_id=s.id AND ar.student_id=e.student_id LEFT JOIN attendance_statuses a ON a.id=ar.attendance_status_id AND a.tenant_id=ar.tenant_id "
                "WHERE s.tenant_id=%s AND s.session_date=%s",(sid(tenant_id),attendance_date)); row=await cur.fetchone()
    roster_count=int(row[0] or 0); marked_count=int(row[1] or 0); present=int(row[2] or 0); absent=int(row[3] or 0); late=int(row[4] or 0); excused=int(row[5] or 0); on_leave=int(row[6] or 0)
    not_marked=max(roster_count-marked_count,0); eligible=max(roster_count-excused-on_leave,0)
    return {"attendance_date":attendance_date,"sessions":int(sessions or 0),"open_sessions":int(open_sessions or 0),"closed_sessions":int(closed_sessions or 0),"roster_count":roster_count,"marked_count":marked_count,"not_marked_count":not_marked,"present_count":present,"absent_count":absent,"late_count":late,"excused_count":excused,"on_leave_count":on_leave,"attendance_rate":rate(present+late,eligible)}
