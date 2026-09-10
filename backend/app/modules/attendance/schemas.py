from datetime import date, datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

AttendanceSource = Literal["manual", "teacher_mobile", "rfid", "biometric", "nfc", "qr", "api", "import", "system"]

class AttendanceSessionCreate(BaseModel):
    academic_year_id: UUID | None = None
    academic_term_id: UUID | None = None
    class_level_id: UUID
    stream_id: UUID | None = None
    timetable_entry_id: UUID | None = None
    session_type: Literal["daily", "lesson", "event"] = "daily"
    session_date: date
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("notes", mode="before")
    @classmethod
    def clean_notes(cls, value):
        if value is None: return None
        value = str(value).strip()
        return value or None

class AttendanceSessionResponse(BaseModel):
    id: UUID; academic_year_id: UUID | None; academic_term_id: UUID | None; class_level_id: UUID | None; stream_id: UUID | None; timetable_entry_id: UUID | None
    session_type: str; session_date: date; scheduled_start_at: datetime | None; scheduled_end_at: datetime | None; actual_started_at: datetime | None; closed_at: datetime | None
    status: str; attendance_policy_id: UUID | None; notes: str | None; roster_count: int = 0; marked_count: int = 0

class RosterStudent(BaseModel):
    student_id: UUID; admission_number: str; first_name: str; middle_name: str | None; last_name: str; class_level_id: UUID; stream_id: UUID | None; enrollment_id: UUID
    status_code: str = "not_marked"; status_name: str = "Not Marked"; late_minutes: int | None = None; marked_at: datetime | None = None; remarks: str | None = None

class AttendanceMarkItem(BaseModel):
    student_id: UUID; status_code: str = Field(min_length=1, max_length=64); marked_at: datetime | None = None; remarks: str | None = Field(default=None, max_length=500)
    @field_validator("status_code", mode="before")
    @classmethod
    def clean_status(cls, value): return str(value).strip().lower()

class AttendanceMarkRequest(BaseModel):
    items: list[AttendanceMarkItem] = Field(min_length=1, max_length=500); source: AttendanceSource = "manual"
    @field_validator("items")
    @classmethod
    def unique_students(cls, value):
        ids = [str(x.student_id) for x in value]
        if len(ids) != len(set(ids)): raise ValueError("A student may only appear once in a marking request")
        return value

class AttendanceMarkResult(BaseModel):
    session_id: UUID; processed: int; created: int; updated: int; results: list[dict]
class AttendanceSessionCloseResponse(BaseModel):
    id: UUID; status: str; closed_at: datetime | None
class AttendanceStatusResponse(BaseModel):
    id: UUID; code: str; name: str; description: str | None; category: str; is_system: bool; is_active: bool; sort_order: int
