from __future__ import annotations
from datetime import date
from uuid import UUID
import re
from pydantic import BaseModel, Field, field_validator
EMAIL_RE=re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$"); PHOTO_URL_RE=re.compile(r"^/api/v1/students/[0-9a-fA-F-]{36}/photo$")
def clean(value:str|None)->str|None:
    if value is None:return None
    value=value.strip(); return value or None
def validate_email(value:str|None)->str|None:
    value=clean(value)
    if value and not EMAIL_RE.match(value):raise ValueError("invalid email address")
    return value
def validate_photo_url(value:str|None)->str|None:
    value=clean(value)
    if value and not PHOTO_URL_RE.fullmatch(value):raise ValueError("photo_url must be a server-managed student photo path")
    return value
class StudentCreate(BaseModel):
    admission_number:str|None=Field(default=None,max_length=80); first_name:str=Field(min_length=1,max_length=100); middle_name:str|None=Field(default=None,max_length=100); last_name:str=Field(min_length=1,max_length=100); date_of_birth:date|None=None; gender:str=Field(default="unspecified",min_length=1,max_length=30); nationality:str|None=Field(default=None,max_length=80); birth_certificate_number:str|None=Field(default=None,max_length=100); admission_date:date|None=None; previous_school:str|None=Field(default=None,max_length=190); status:str=Field(default="active",min_length=1,max_length=40); medical_notes:str|None=None; emergency_notes:str|None=None
    @field_validator("admission_number",mode="before")
    @classmethod
    def trim_admission_number(cls,value):return clean(value)
    @field_validator("first_name","last_name",mode="before")
    @classmethod
    def trim_required(cls,value):
        if not isinstance(value,str) or not value.strip():raise ValueError("value cannot be empty")
        return value.strip()
    @field_validator("middle_name","nationality","birth_certificate_number","previous_school","medical_notes","emergency_notes",mode="before")
    @classmethod
    def trim_optional(cls,value):return clean(value)
class StudentUpdate(BaseModel):
    first_name:str|None=Field(default=None,min_length=1,max_length=100); middle_name:str|None=Field(default=None,max_length=100); last_name:str|None=Field(default=None,min_length=1,max_length=100); date_of_birth:date|None=None; gender:str|None=Field(default=None,min_length=1,max_length=30); nationality:str|None=Field(default=None,max_length=80); birth_certificate_number:str|None=Field(default=None,max_length=100); admission_date:date|None=None; previous_school:str|None=Field(default=None,max_length=190); status:str|None=Field(default=None,min_length=1,max_length=40); medical_notes:str|None=None; emergency_notes:str|None=None
class StudentResponse(StudentCreate): admission_number:str; id:UUID; photo_url:str|None=None; is_active:bool=True; current_class_name:str|None=None; current_stream_name:str|None=None
class GuardianCreate(BaseModel):
    first_name:str=Field(min_length=1,max_length=100); last_name:str=Field(min_length=1,max_length=100); phone:str|None=Field(default=None,max_length=40); alternative_phone:str|None=Field(default=None,max_length=40); email:str|None=None; address:str|None=Field(default=None,max_length=255); occupation:str|None=Field(default=None,max_length=150); employer:str|None=Field(default=None,max_length=190); preferred_contact_method:str=Field(default="phone",min_length=1,max_length=40); status:str=Field(default="active",min_length=1,max_length=40)
    @field_validator("email")
    @classmethod
    def email_valid(cls,value):return validate_email(value)
class GuardianUpdate(BaseModel):
    first_name:str|None=Field(default=None,min_length=1,max_length=100); last_name:str|None=Field(default=None,min_length=1,max_length=100); phone:str|None=Field(default=None,max_length=40); alternative_phone:str|None=Field(default=None,max_length=40); email:str|None=None; address:str|None=Field(default=None,max_length=255); occupation:str|None=Field(default=None,max_length=150); employer:str|None=Field(default=None,max_length=190); preferred_contact_method:str|None=Field(default=None,min_length=1,max_length=40); status:str|None=Field(default=None,min_length=1,max_length=40)
    @field_validator("email")
    @classmethod
    def email_valid(cls,value):return validate_email(value)
class GuardianResponse(GuardianCreate): id:UUID
class StudentGuardianCreate(BaseModel): guardian_id:UUID; relationship:str=Field(min_length=2,max_length=80); is_primary:bool=False; is_emergency_contact:bool=False; can_pick_up:bool=True
class StudentGuardianResponse(StudentGuardianCreate): id:UUID; student_id:UUID; guardian:GuardianResponse
class EnrollmentCreate(BaseModel): academic_year_id:UUID; class_level_id:UUID; stream_id:UUID|None=None; enrollment_date:date; exit_date:date|None=None; status:str=Field(default="active",min_length=1,max_length=40); notes:str|None=None
class EnrollmentUpdate(BaseModel): enrollment_date:date|None=None; exit_date:date|None=None; status:str|None=Field(default=None,min_length=1,max_length=40); notes:str|None=None
class EnrollmentResponse(EnrollmentCreate): id:UUID; student_id:UUID; academic_year_name:str; class_name:str; stream_name:str|None
class DocumentTypeCreate(BaseModel): code:str=Field(min_length=2,max_length=80); name:str=Field(min_length=2,max_length=160); is_required:bool=False
class DocumentTypeResponse(DocumentTypeCreate): id:UUID
class StudentDocumentCreate(BaseModel): document_type_id:UUID; file_name:str=Field(min_length=1,max_length=255); file_url:str=Field(min_length=1,max_length=500); issued_date:date|None=None; expiry_date:date|None=None; notes:str|None=None
class StudentDocumentResponse(StudentDocumentCreate): id:UUID; student_id:UUID; document_type_name:str
class AdmissionNumberSettings(BaseModel): prefix:str=Field(default="ADM",max_length=30); separator:str=Field(default="-",max_length=5); include_year:bool=True; year_format:str=Field(default="YYYY",min_length=2,max_length=4); padding:int=Field(default=4,ge=1,le=10); start:int=Field(default=1,ge=1,le=1_000_000_000); reset_yearly:bool=True
class StudentDetailResponse(StudentResponse): guardians:list[StudentGuardianResponse]=Field(default_factory=list); enrollments:list[EnrollmentResponse]=Field(default_factory=list); documents:list[StudentDocumentResponse]=Field(default_factory=list)
