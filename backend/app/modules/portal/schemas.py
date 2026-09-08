from datetime import date
from pydantic import BaseModel


class PortalAcademicContext(BaseModel):
    id: str
    name: str


class PortalEnrollment(BaseModel):
    id: str | None = None
    enrollment_date: date | None = None
    status: str | None = None
    academic_year: PortalAcademicContext | None = None
    class_: PortalAcademicContext | None = None
    stream: PortalAcademicContext | None = None

    model_config = {"populate_by_name": True}

    @classmethod
    def from_mapping(cls, value):
        if value is None:
            return None
        return cls(
            id=value.get("id"), enrollment_date=value.get("enrollment_date"), status=value.get("status"),
            academic_year=value.get("academic_year"), class_=value.get("class"), stream=value.get("stream")
        )


class StudentPortalProfile(BaseModel):
    id: str
    admission_number: str
    first_name: str
    middle_name: str | None = None
    last_name: str
    date_of_birth: date | None = None
    gender: str | None = None
    nationality: str | None = None
    admission_date: date | None = None
    photo_url: str | None = None
    status: str
    enrollment: PortalEnrollment | None = None


class StudentPortalResponse(BaseModel):
    portal: str = "student"
    profile: StudentPortalProfile


class ParentChild(BaseModel):
    id: str
    admission_number: str
    first_name: str
    middle_name: str | None = None
    last_name: str
    date_of_birth: date | None = None
    gender: str | None = None
    photo_url: str | None = None
    status: str
    relationship: str | None = None
    is_primary: bool = False
    is_emergency_contact: bool = False
    can_pick_up: bool = False
    enrollment: PortalEnrollment | None = None


class ParentPortalProfile(BaseModel):
    id: str
    first_name: str
    last_name: str
    phone: str | None = None
    alternative_phone: str | None = None
    email: str | None = None
    address: str | None = None
    occupation: str | None = None
    employer: str | None = None
    preferred_contact_method: str | None = None
    status: str


class ParentPortalResponse(BaseModel):
    portal: str = "parent"
    profile: ParentPortalProfile
    children: list[ParentChild] = []
