from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import Principal, get_current_principal, require_tenant_permission
from app.core.database import get_pool

router = APIRouter(prefix="/portal", tags=["Portal"])

@router.get("/me")
async def portal_me(principal: Principal = Depends(get_current_principal), tenant_id=Depends(require_tenant_permission("portal.dashboard"))):
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            permissions = await _permissions(cur, tenant_id, principal.user_id)
            if "guardian.self" in permissions:
                await cur.execute("SELECT id,first_name,last_name,phone,email FROM guardians WHERE tenant_id=%s AND tenant_user_id=%s LIMIT 1", (str(tenant_id), str(principal.user_id)))
                guardian = await cur.fetchone()
                if not guardian:
                    raise HTTPException(404, "Guardian profile not found")
                await cur.execute("SELECT s.id,s.admission_number,s.first_name,s.middle_name,s.last_name,s.status FROM students s JOIN student_guardians sg ON sg.student_id=s.id WHERE sg.tenant_id=%s AND sg.guardian_id=%s ORDER BY s.last_name,s.first_name", (str(tenant_id), str(guardian[0])))
                children = [dict(id=str(r[0]), admission_number=r[1], first_name=r[2], middle_name=r[3], last_name=r[4], status=r[5]) for r in await cur.fetchall()]
                return {"portal": "parent", "profile": {"id": str(guardian[0]), "first_name": guardian[1], "last_name": guardian[2], "phone": guardian[3], "email": guardian[4]}, "children": children}
            if "student.self" in permissions:
                await cur.execute("SELECT id,admission_number,first_name,middle_name,last_name,date_of_birth,gender,status FROM students WHERE tenant_id=%s AND tenant_user_id=%s LIMIT 1", (str(tenant_id), str(principal.user_id)))
                student = await cur.fetchone()
                if not student:
                    raise HTTPException(404, "Student profile not found")
                return {"portal": "student", "profile": {"id": str(student[0]), "admission_number": student[1], "first_name": student[2], "middle_name": student[3], "last_name": student[4], "date_of_birth": student[5], "gender": student[6], "status": student[7]}}
            return {"portal": "staff", "profile": {"user_id": str(principal.user_id)}}

async def _permissions(cur, tenant_id, user_id):
    await cur.execute("SELECT DISTINCT p.code FROM tenant_memberships m JOIN tenant_membership_roles mr ON mr.membership_id=m.id JOIN tenant_roles r ON r.id=mr.role_id JOIN tenant_role_permissions rp ON rp.role_id=r.id JOIN tenant_permissions p ON p.id=rp.permission_id WHERE m.tenant_id=%s AND m.tenant_user_id=%s AND m.status='active'", (str(tenant_id), str(user_id)))
    return {str(r[0]) for r in await cur.fetchall()}
