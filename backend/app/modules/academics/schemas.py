from datetime import date, time
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

def clean(value):
    if value is None: return None
    if isinstance(value, str): value = value.strip(); return value or None
    return value

class TeacherCreate(BaseModel):
    tenant_user_id: UUID | None = None; teacher_number: str = Field(min_length=1, max_length=80); first_name: str = Field(min_length=1, max_length=100); middle_name: str | None = Field(default=None, max_length=100); last_name: str = Field(min_length=1, max_length=100); gender: str = Field(default='unspecified', min_length=1, max_length=30); phone: str | None = Field(default=None, max_length=40); email: str | None = Field(default=None, max_length=190); department_id: UUID | None = None; subject_ids: list[UUID] = Field(default_factory=list); employment_type: str | None = Field(default=None, max_length=60); employment_date: date | None = None; status: str = Field(default='active', min_length=1, max_length=40); notes: str | None = None
    @field_validator('teacher_number','first_name','middle_name','last_name','phone','email','employment_type','notes','gender','status', mode='before')
    @classmethod
    def trim(cls, v): return clean(v)
    @field_validator('subject_ids')
    @classmethod
    def unique_subjects(cls, v):
        if len({str(x) for x in v}) != len(v): raise ValueError('A subject can only be selected once')
        return v
class TeacherUpdate(BaseModel):
    tenant_user_id: UUID | None = None; teacher_number: str | None = Field(default=None, min_length=1, max_length=80); first_name: str | None = Field(default=None, min_length=1, max_length=100); middle_name: str | None = Field(default=None, max_length=100); last_name: str | None = Field(default=None, min_length=1, max_length=100); gender: str | None = Field(default=None, min_length=1, max_length=30); phone: str | None = Field(default=None, max_length=40); email: str | None = Field(default=None, max_length=190); department_id: UUID | None = None; subject_ids: list[UUID] | None = Field(default=None); employment_type: str | None = Field(default=None, max_length=60); employment_date: date | None = None; status: str | None = Field(default=None, min_length=1, max_length=40); notes: str | None = None
    @field_validator('teacher_number','first_name','middle_name','last_name','phone','email','employment_type','notes','gender','status', mode='before')
    @classmethod
    def trim(cls, v): return clean(v)
    @field_validator('subject_ids')
    @classmethod
    def unique_subjects(cls, v):
        if v is not None and len({str(x) for x in v}) != len(v): raise ValueError('A subject can only be selected once')
        return v
class TeacherResponse(TeacherCreate): id: UUID; department_name: str | None = None; subjects: list[dict] = Field(default_factory=list)
class BulkTeacherUpdate(BaseModel): teacher_ids: list[UUID] = Field(min_length=1, max_length=500); department_id: UUID | None = None; employment_type: str | None = Field(default=None, max_length=60); status: str | None = Field(default=None, min_length=1, max_length=40); gender: str | None = Field(default=None, min_length=1, max_length=30)
class BulkTeacherSubjects(BaseModel):
    teacher_ids: list[UUID] = Field(min_length=1, max_length=500); subject_ids: list[UUID] = Field(min_length=0)
    @field_validator('teacher_ids','subject_ids')
    @classmethod
    def unique_ids(cls, v):
        if len({str(x) for x in v}) != len(v): raise ValueError('Duplicate IDs are not allowed')
        return v
class AssignmentCreate(BaseModel): teacher_id: UUID; academic_year_id: UUID; academic_term_id: UUID; class_level_id: UUID; stream_id: UUID | None = None; subject_id: UUID
class AssignmentResponse(AssignmentCreate): id: UUID; teacher_name: str; class_name: str; stream_name: str | None; subject_name: str; academic_year_name: str; academic_term_name: str
class RoomCreate(BaseModel): code: str = Field(min_length=1, max_length=60); name: str = Field(min_length=1, max_length=120); capacity: int | None = Field(default=None, ge=1, le=100000); room_type: str | None = Field(default=None, max_length=80); is_active: bool = True
class RoomUpdate(RoomCreate): pass
class RoomResponse(RoomCreate): id: UUID
class PeriodCreate(BaseModel):
    code: str = Field(min_length=1, max_length=60); name: str = Field(min_length=1, max_length=120); start_time: time; end_time: time; is_break: bool = False; sort_order: int = Field(ge=1, le=1000); is_active: bool = True
    @field_validator('end_time')
    @classmethod
    def valid_time(cls, v, info):
        start = info.data.get('start_time')
        if start and v <= start: raise ValueError('end_time must be after start_time')
        return v
class PeriodUpdate(PeriodCreate): pass
class PeriodResponse(PeriodCreate): id: UUID
class TimetableCreate(BaseModel):
    academic_year_id: UUID; academic_term_id: UUID; class_level_id: UUID; stream_id: UUID | None = None; subject_id: UUID; teacher_id: UUID; room_id: UUID | None = None; period_id: UUID; day_of_week: int = Field(ge=1, le=7); duration_periods: int = Field(default=1, ge=1, le=12); is_double: bool = False; notes: str | None = Field(default=None, max_length=500)
class TimetableResponse(TimetableCreate): id: UUID; teacher_name: str; class_name: str; stream_name: str | None; subject_name: str; room_name: str | None; period_name: str
class GenerateRequest(BaseModel): academic_year_id: UUID; academic_term_id: UUID; class_level_id: UUID | None = None; stream_id: UUID | None = None; lessons_per_week: int | None = Field(default=None, ge=1, le=40); replace_existing: bool = False
class GenerateResponse(BaseModel): created: int; skipped: int; conflicts: list[str]
class EffectiveAcademicSettingsResponse(BaseModel): settings: dict[str, object]; reference_values: dict[str, list[dict]]; curriculum: dict[str, object]
