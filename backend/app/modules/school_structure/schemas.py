from datetime import date
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

class CampusCreate(BaseModel):
    code: str = Field(min_length=2,max_length=40); name: str = Field(min_length=2,max_length=160)
    address: str|None=None; phone: str|None=None; email: str|None=None; is_main: bool=False
class CampusResponse(CampusCreate): id: UUID; is_active: bool

class AcademicYearCreate(BaseModel):
    name: str=Field(min_length=2,max_length=80); start_date: date; end_date: date; is_current: bool=False
    @field_validator('end_date')
    @classmethod
    def valid_range(cls,v,info):
        if info.data.get('start_date') and v<=info.data['start_date']: raise ValueError('end_date must be after start_date')
        return v
class AcademicYearResponse(AcademicYearCreate): id: UUID; is_active: bool

class TermCreate(BaseModel):
    academic_year_id: UUID; name: str=Field(min_length=2,max_length=80); term_number: int=Field(ge=1,le=4); start_date: date; end_date: date; is_current: bool=False
    @field_validator('end_date')
    @classmethod
    def valid_range(cls,v,info):
        if info.data.get('start_date') and v<=info.data['start_date']: raise ValueError('end_date must be after start_date')
        return v
class TermResponse(TermCreate): id: UUID; is_active: bool

class DepartmentCreate(BaseModel): code: str=Field(min_length=2,max_length=40); name: str=Field(min_length=2,max_length=120); description: str|None=None
class DepartmentResponse(DepartmentCreate): id: UUID; is_active: bool

class ClassLevelCreate(BaseModel): code: str=Field(min_length=1,max_length=40); name: str=Field(min_length=2,max_length=100); level_order: int=0
class ClassLevelResponse(ClassLevelCreate): id: UUID; is_active: bool

class StreamCreate(BaseModel): class_level_id: UUID; code: str=Field(min_length=1,max_length=40); name: str=Field(min_length=2,max_length=100); capacity: int|None=Field(default=None,ge=1,le=100000)
class StreamResponse(StreamCreate): id: UUID; is_active: bool

class SubjectCreate(BaseModel):
    department_id: UUID|None=None; code: str=Field(min_length=1,max_length=40); name: str=Field(min_length=2,max_length=120); short_name: str|None=None
    subject_type: str=Field(default='core',pattern='^(core|elective|co_curricular)$')
class SubjectResponse(SubjectCreate): id: UUID; is_active: bool

class ClassSubjectCreate(BaseModel): class_level_id: UUID; subject_id: UUID; is_compulsory: bool=True
class ClassSubjectResponse(ClassSubjectCreate): id: UUID

class SettingUpdate(BaseModel): value: str|None=None; value_type: str=Field(default='string',pattern='^(string|integer|boolean|json)$')
class SettingResponse(BaseModel): setting_key: str; setting_value: str|None; value_type: str
