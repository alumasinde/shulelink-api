from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

ExemptionType = Literal['leave', 'sickbay', 'suspension', 'official_duty', 'approved_absence']

class AttendanceCorrectionCreate(BaseModel):
    attendance_record_id: UUID
    new_status_code: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=3, max_length=500)
    @field_validator('new_status_code', 'reason', mode='before')
    @classmethod
    def clean_text(cls, value):
        return str(value).strip()

class AttendanceCorrectionResponse(BaseModel):
    id: UUID
    attendance_record_id: UUID
    previous_status_id: UUID | None
    previous_status_code: str | None
    new_status_id: UUID
    new_status_code: str
    reason: str
    requested_by_user_id: UUID
    approved_by_user_id: UUID | None
    status: str
    requested_at: datetime
    approved_at: datetime | None
    resolved_at: datetime | None

class AttendanceExemptionCreate(BaseModel):
    student_id: UUID
    exemption_type: ExemptionType
    starts_at: datetime
    ends_at: datetime
    reason: str | None = Field(default=None, max_length=500)
    source_type: str | None = Field(default=None, max_length=64)
    source_id: UUID | None = None
    @field_validator('reason', 'source_type', mode='before')
    @classmethod
    def clean_optional_text(cls, value):
        if value is None: return None
        value = str(value).strip()
        return value or None

class AttendanceExemptionResponse(BaseModel):
    id: UUID
    student_id: UUID
    exemption_type: str
    status: str
    starts_at: datetime
    ends_at: datetime
    reason: str | None
    source_type: str | None
    source_id: UUID | None
    created_by_user_id: UUID | None
    requested_by_user_id: UUID | None
    approved_by_user_id: UUID | None
    approved_at: datetime | None
    resolved_at: datetime | None
