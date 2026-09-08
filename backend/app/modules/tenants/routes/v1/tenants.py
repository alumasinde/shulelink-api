from uuid import UUID
from fastapi import APIRouter, Depends
from app.core.dependencies import Principal, require_platform_permission
from app.modules.auth.schemas import CreateTenantRequest, TenantResponse
from app.modules.tenants.schemas import CreateTenantUserRequest, TenantUserResponse
from app.modules.tenants.service import create_tenant, list_tenants
from app.modules.tenants.users import create_tenant_user

router = APIRouter(prefix="/tenants", tags=["Tenants"])

@router.post("", response_model=TenantResponse, status_code=201)
async def create(payload: CreateTenantRequest, _: Principal = Depends(require_platform_permission("tenants.manage"))):
    return await create_tenant(payload)

@router.get("", response_model=list[TenantResponse])
async def list_all(_: Principal = Depends(require_platform_permission("tenants.manage"))):
    return await list_tenants()

@router.post("/{tenant_id}/users", response_model=TenantUserResponse, status_code=201)
async def create_user(tenant_id: UUID, payload: CreateTenantUserRequest, _: Principal = Depends(require_platform_permission("tenants.manage"))):
    return await create_tenant_user(tenant_id, payload)
