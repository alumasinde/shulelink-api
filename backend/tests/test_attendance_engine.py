from uuid import uuid4
import pytest
from app.modules.attendance.schemas import AttendanceMarkRequest

def test_attendance_mark_request_rejects_duplicate_students():
    sid=str(uuid4())
    with pytest.raises(ValueError, match='only appear once'):
        AttendanceMarkRequest.model_validate({'items':[{'student_id':sid,'status_code':'present'},{'student_id':sid,'status_code':'absent'}]})
