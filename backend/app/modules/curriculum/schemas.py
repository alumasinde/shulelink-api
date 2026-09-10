from datetime import date
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class CurriculumLevel(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    sequence_no: int = 0


class CurriculumGrade(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    education_level_code: str = Field(min_length=1, max_length=80)
    sequence_no: int = 0


class CurriculumLearningArea(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=180)
    description: str | None = None
    sequence_no: int = 0


class CurriculumSubject(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=180)
    learning_area_code: str | None = None
    subject_type: str = Field(default='core', min_length=1, max_length=80)
    description: str | None = None
    sequence_no: int = 0


class CurriculumOffering(BaseModel):
    grade_code: str
    subject_code: str
    pathway_code: str | None = None
    track_code: str | None = None
    requirement_type: str = Field(default='required', min_length=1, max_length=60)
    weekly_periods: float | None = Field(default=None, ge=0, le=100)


class CurriculumPathway(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=180)
    description: str | None = None
    sequence_no: int = 0


class CurriculumTrack(BaseModel):
    pathway_code: str
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=180)
    description: str | None = None
    sequence_no: int = 0


class CurriculumCombination(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=180)
    grade_code: str | None = None
    pathway_code: str | None = None
    track_code: str | None = None
    description: str | None = None
    subjects: list[str] = Field(default_factory=list)


class CurriculumTemplateDocument(BaseModel):
    model_config = ConfigDict(extra='forbid')
    levels: list[CurriculumLevel] = Field(default_factory=list)
    grades: list[CurriculumGrade] = Field(default_factory=list)
    learning_areas: list[CurriculumLearningArea] = Field(default_factory=list)
    subjects: list[CurriculumSubject] = Field(default_factory=list)
    offerings: list[CurriculumOffering] = Field(default_factory=list)
    pathways: list[CurriculumPathway] = Field(default_factory=list)
    tracks: list[CurriculumTrack] = Field(default_factory=list)
    combinations: list[CurriculumCombination] = Field(default_factory=list)


class CurriculumTemplateCreate(BaseModel):
    code: str = Field(min_length=2, max_length=100, pattern=r'^[a-z0-9][a-z0-9_-]*$')
    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    country_code: str | None = Field(default=None, max_length=10)
    framework_code: str = Field(default='kenya_cbc', min_length=1, max_length=100)
    effective_from: date | None = None
    effective_to: date | None = None
    is_default: bool = False
    document: CurriculumTemplateDocument = Field(default_factory=CurriculumTemplateDocument)


class CurriculumTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    country_code: str | None = Field(default=None, max_length=10)
    framework_code: str | None = Field(default=None, max_length=100)
    effective_from: date | None = None
    effective_to: date | None = None
    document: CurriculumTemplateDocument | None = None


class CurriculumTemplateSummary(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None
    country_code: str | None
    framework_code: str
    version_no: int
    status: str
    effective_from: date | None
    effective_to: date | None
    is_default: bool
    counts: dict[str, int]


class CurriculumTemplateResponse(CurriculumTemplateSummary):
    document: CurriculumTemplateDocument


class CurriculumTemplateCloneRequest(BaseModel):
    code: str | None = Field(default=None, max_length=100, pattern=r'^[a-z0-9][a-z0-9_-]*$')
    name: str | None = Field(default=None, max_length=200)


class CurriculumSelectRequest(BaseModel):
    template_id: UUID
    allow_local_customization: bool = True
