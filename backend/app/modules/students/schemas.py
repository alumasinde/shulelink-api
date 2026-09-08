from __future__ import annotations

from datetime import date
from uuid import UUID
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def validate_email(value: str | None) -> str | None:
    value = clean(value)
    if value and not EMAIL_RE.match(value):
        raise ValueError("invalid email address")
    return value


class StudentCreate(BaseModel):
    admission_number: str = Field(min_length=1, max_length=80)
    first_name: str = Field(min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    date_of_birth: date | None = None
    gender: str = Field(default="unspecified", pattern="^(male|female|other|unspecified)$")
    nationality: str | None = Field(default=None, max_length=80)
    birth_certificate_number: str | None = Field(default=None, max_length=100)
    admission_date: date | None = None
    previous_school: str | None = Field(default=None, max_length=190)
    photo_url: str | None = Field(default=None, max_length=500)
    status: str = Field(default="active", pattern="^(active|inactive|graduated|transferred|withdrawn)$")
    medical_notes: str | None = None
    emergency_notes: str | None = None

    @field_validator("admission_number", "first_name", "last_name", mode="before")
    @classmethod
    def trim_required(cls, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("value cannot be empty")
        return value.strip()

    @field_validator("middle_name", "nationality", "birth_certificate_number", "previous_school", "photo_url", "medical_notes", "emergency_notes", mode="before")
    @classmethod
    def trim_optional(cls, value):
        return clean(value)


class StudentUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, pattern="^(male|female|other|unspecified)$")
    nationality: str | None = Field(default=None, max_length=80)
    birth_certificate_number: str | None = Field(default=None, max_length=100)
    admission_date: date | None = None
    previous_school: str | None = Field(default=None, max_length=190)
    photo_url: str | None = Field(default=None, max_length=500)
    status: str | None = Field(default=None, pattern="^(active|inactive|graduated|transferred|withdrawn)$")
    medical_notes: str | None = None
    emergency_notes: str | None = None


class StudentResponse(StudentCreate):
    id: UUID
    is_active: bool = True
    model_config = ConfigDict(from_attributes=True)


class GuardianCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=40)
    alternative_phone: str | None = Field(default=None, max_length=40)
    email: str | None = None
    address: str | None = Field(default=None, max_length=255)
    occupation: str | None = Field(default=None, max_length=150)
    employer: str | None = Field(default=None, max_length=190)
    preferred_contact_method: str = Field(default="phone", pattern="^(phone|sms|email|whatsapp|any)$")
    status: str = Field(default="active", pattern="^(active|inactive)$")

    _email = field_validator("email")(validate_email)


class GuardianUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=40)
    alternative_phone: str | None = Field(default=None, max_length=40)
    email: str | None = None
    address: str | None = Field(default=None, max_length=255)
    occupation: str | None = Field(default=None, max_length=150)
    employer: str | None = Field(default=None, max_length=190)
    preferred_contact_method: str | None = Field(default=None, pattern="^(phone|sms|email|whatsapp|any)$")
    status: str | None = Field(default=None, pattern="^(active|inactive)$")

    _email = field_validator("email")(validate_email)


class GuardianResponse(GuardianCreate):
    id: UUID


class StudentGuardianCreate(BaseModel):
    guardian_id: UUID
    relationship: str = Field(min_length=1, max_length=80)
    is_primary: bool = False
    is_emergency_contact: bool = False
    can_pick_up: bool = True

    @field_validator("relationship", mode="before")
    @classmethod
    def trim_relationship(cls, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("relationship cannot be empty")
        return value.strip()


class StudentGuardianResponse(StudentGuardianCreate):
    id: UUID
    student_id: UUID
    guardian: GuardianResponse | None = None


class EnrollmentCreate(BaseModel):
    academic_year_id: UUID
    class_level_id: UUID
    stream_id: UUID | None = None
    enrollment_date: date
    exit_date: date | None = None
    status: str = Field(default="active", pattern="^(active|completed|withdrawn)$")
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def valid_dates(self):
        if self.exit_date and self.exit_date < self.enrollment_date:
            raise ValueError("exit_date cannot be before enrollment_date")
        return self


class EnrollmentUpdate(BaseModel):
    stream_id: UUID | None = None
    enrollment_date: date | None = None
    exit_date: date | None = None
    status: str | None = Field(default=None, pattern="^(active|completed|withdrawn)$")
    notes: str | None = Field(default=None, max_length=500)


class EnrollmentResponse(EnrollmentCreate):
    id: UUID
    student_id: UUID
    academic_year_name: str | None = None
    class_name: str | None = None
    stream_name: str | None = None


class DocumentTypeCreate(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=150)
    is_required: bool = False
    is_active: bool = True


class DocumentTypeResponse(DocumentTypeCreate):
    id: UUID


class StudentDocumentCreate(BaseModel):
    document_type_id: UUID
    file_name: str = Field(min_length=1, max_length=255)
    file_url: str = Field(min_length=1, max_length=1000)
    mime_type: str | None = Field(default=None, max_length=120)
    file_size: int | None = Field(default=None, ge=0)
    document_number: str | None = Field(default=None, max_length=150)
    issued_at: date | None = None
    expires_at: date | None = None
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def valid_dates(self):
        if self.issued_at and self.expires_at and self.expires_at < self.issued_at:
            raise ValueError("expires_at cannot be before issued_at")
        return self


class StudentDocumentResponse(StudentDocumentCreate):
    id: UUID
    student_id: UUID
    document_type_name: str | None = None
    uploaded_by: UUID | None = None


class StudentDetailResponse(StudentResponse):
    guardians: list[StudentGuardianResponse] = []
    enrollments: list[EnrollmentResponse] = []
    documents: list[StudentDocumentResponse] = []
