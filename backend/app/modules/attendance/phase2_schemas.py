from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class AttendanceSessionListItem(BaseModel):
    id: UUID
    session_date: date
    session_type: str
    class_level_id: UUID
    stream_id: UUID | None
    status: str
    scheduled_start_at: datetime | None
    scheduled_end_at: datetime | None
    roster_count: int
    marked_count: int
    not_marked_count: int
    attendance_rate: float


class AttendanceDashboard(BaseModel):
    attendance_date: date
    sessions: int
    open_sessions: int
    closed_sessions: int
    roster_count: int
    marked_count: int
    not_marked_count: int
    present_count: int
    absent_count: int
    late_count: int
    excused_count: int
    on_leave_count: int
    attendance_rate: float


class AttendanceSessionCompletion(BaseModel):
    session_id: UUID
    status: str
    roster_count: int
    marked_count: int
    not_marked_count: int
    completion_rate: float
    attendance_rate: float
    can_close: bool
    requires_override: bool
