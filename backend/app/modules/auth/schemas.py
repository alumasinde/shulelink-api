from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime


class MeResponse(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    user_type: str
    tenant_id: UUID | None = None
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    portal: str = "school"


class ActivateAccountRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    password: str = Field(min_length=8, max_length=128)


class ActivationResponse(BaseModel):
    success: bool = True
    message: str
    email: str
    expires_at: datetime | None = None


class CreateTenantRequest(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    slug: str = Field(min_length=2, max_length=80)
    database_mode: str = Field(default="shared")

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        import re
        value = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", value):
            raise ValueError("Slug must contain only lowercase letters, numbers and hyphens")
        return value

    @field_validator("database_mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        if value not in {"shared", "dedicated"}:
            raise ValueError("database_mode must be shared or dedicated")
        return value


class TenantResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    status: str
    database_mode: str
    host: str
