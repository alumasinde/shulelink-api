from uuid import UUID
from pydantic import BaseModel, Field

class CreateTenantUserRequest(BaseModel):
    email: str
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=10, max_length=128)
    role_code: str = Field(default="school_admin", min_length=2, max_length=80)

class TenantUserResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    email: str
    first_name: str
    last_name: str
    role_code: str
    status: str
