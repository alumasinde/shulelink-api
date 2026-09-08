from datetime import date
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator

class CampusCreate(BaseModel):
    code: str=Field(min_length=2,max_length=40); name: str=Field(min_length=2,max_length=160); address: str|None=None; phone: str|None=None; email: str|None=None; is_main: bool=False
    @field_validator('code','name',mode='before')
    @classmethod
    def clean_required(cls,v):
        if not isinstance(v,str) or not v.strip(): raise ValueError('value cannot be empty')
        return v.strip()
class CampusUpdate(BaseModel):
    code: str|None=Field(default=None,min_length=2,max_length=40); name: str|None=Field(default=None,min_length=2,max_length=160); address: str|None=None; phone: str|None=None; email: str|None=None; is_main: bool|None=None; is_active: bool|None=None
class CampusResponse(CampusCreate): id: UUID; is_active: bool

class AcademicYearCreate(BaseModel):
    name: str=Field(min_length=2,max_length=80); start_date: date; end_date: date; is_current: bool=False
    @field_validator('name',mode='before')
    @classmethod
    def clean_name(cls,v): return v.strip() if isinstance(v,str) else v
    @field_validator('end_date')
    @classmethod
    def valid_range(cls,v,info):
        if info.data.get('start_date') and v<=info.data['start_date']: raise ValueError('end_date must be after start_date')
        return v
class AcademicYearUpdate(BaseModel):
    name: str|None=Field(default=None,min_length=2,max_length=80); start_date: date|None=None; end_date: date|None=None; is_current: bool|None=None; is_active: bool|None=None
    @model_validator(mode='after')
    def valid_range(self):
        if self.start_date and self.end_date and self.end_date<=self.start_date: raise ValueError('end_date must be after start_date')
        return self
class AcademicYearResponse(AcademicYearCreate): id: UUID; is_active: bool

class TermCreate(BaseModel):
    academic_year_id: UUID; name: str=Field(min_length=2,max_length=80); term_number: int=Field(ge=1,le=4); start_date: date; end_date: date; is_current: bool=False
    @field_validator('end_date')
    @classmethod
    def valid_range(cls,v,info):
        if info.data.get('start_date') and v<=info.data['start_date']: raise ValueError('end_date must be after start_date')
        return v
class TermUpdate(BaseModel):
    academic_year_id: UUID|None=None; name: str|None=Field(default=None,min_length=2,max_length=80); term_number: int|None=Field(default=None,ge=1,le=4); start_date: date|None=None; end_date: date|None=None; is_current: bool|None=None; is_active: bool|None=None
    @model_validator(mode='after')
    def valid_range(self):
        if self.start_date and self.end_date and self.end_date<=self.start_date: raise ValueError('end_date must be after start_date')
        return self
class TermResponse(TermCreate): id: UUID; is_active: bool

class DepartmentCreate(BaseModel): code: str=Field(min_length=2,max_length=40); name: str=Field(min_length=2,max_length=120); description: str|None=None
class DepartmentUpdate(BaseModel): code: str|None=Field(default=None,min_length=2,max_length=40); name: str|None=Field(default=None,min_length=2,max_length=120); description: str|None=None; is_active: bool|None=None
class DepartmentResponse(DepartmentCreate): id: UUID; is_active: bool

class ClassLevelCreate(BaseModel): code: str=Field(min_length=1,max_length=40); name: str=Field(min_length=2,max_length=100); level_order: int=0
class ClassLevelUpdate(BaseModel): code: str|None=Field(default=None,min_length=1,max_length=40); name: str|None=Field(default=None,min_length=2,max_length=100); level_order: int|None=None; is_active: bool|None=None
class ClassLevelResponse(ClassLevelCreate): id: UUID; is_active: bool

class StreamCreate(BaseModel): class_level_id: UUID; code: str=Field(min_length=1,max_length=40); name: str=Field(min_length=2,max_length=100); capacity: int|None=Field(default=None,ge=1,le=100000)
class StreamUpdate(BaseModel): class_level_id: UUID|None=None; code: str|None=Field(default=None,min_length=1,max_length=40); name: str|None=Field(default=None,min_length=2,max_length=100); capacity: int|None=Field(default=None,ge=1,le=100000); is_active: bool|None=None
class StreamResponse(StreamCreate): id: UUID; is_active: bool

class SubjectCreate(BaseModel):
    department_id: UUID|None=None; code: str=Field(min_length=1,max_length=40); name: str=Field(min_length=2,max_length=120); short_name: str|None=None; subject_type: str=Field(default='core',pattern='^(core|elective|co_curricular)$')
class SubjectUpdate(BaseModel):
    department_id: UUID|None=None; code: str|None=Field(default=None,min_length=1,max_length=40); name: str|None=Field(default=None,min_length=2,max_length=120); short_name: str|None=None; subject_type: str|None=Field(default=None,pattern='^(core|elective|co_curricular)$'); is_active: bool|None=None
class SubjectResponse(SubjectCreate): id: UUID; is_active: bool

class ClassSubjectCreate(BaseModel): class_level_id: UUID; subject_id: UUID; is_compulsory: bool=True
class ClassSubjectUpdate(BaseModel): is_compulsory: bool
class ClassSubjectResponse(ClassSubjectCreate): id: UUID

class SettingUpdate(BaseModel): value: str|None=None; value_type: str=Field(default='string',pattern='^(string|integer|boolean|json)$')
class SettingResponse(BaseModel): setting_key: str; setting_value: str|None; value_type: str
