from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.modules.attendance.engine import evaluate_status, request_fingerprint
from app.modules.attendance.schemas import AttendanceMarkRequest


def test_attendance_mark_request_rejects_duplicate_students():
    sid = str(uuid4())
    with pytest.raises(ValueError, match="only appear once"):
        AttendanceMarkRequest.model_validate(
            {
                "items": [
                    {"student_id": sid, "status_code": "present"},
                    {"student_id": sid, "status_code": "absent"},
                ]
            }
        )


def test_present_becomes_late_after_grace_period():
    scheduled = datetime(2026, 9, 10, 8, 0)
    effective, late = evaluate_status(
        "present", scheduled + timedelta(minutes=16), scheduled, 15
    )
    assert effective == "late"
    assert late == 16


def test_present_within_grace_remains_present():
    scheduled = datetime(2026, 9, 10, 8, 0)
    effective, late = evaluate_status(
        "present", scheduled + timedelta(minutes=15), scheduled, 15
    )
    assert effective == "present"
    assert late is None


def test_not_marked_cannot_be_captured():
    with pytest.raises(Exception, match="cannot be used for attendance capture"):
        evaluate_status("not_marked", datetime(2026, 9, 10, 8, 0), None, 0)


def test_idempotency_fingerprint_changes_when_request_changes():
    first = AttendanceMarkRequest.model_validate(
        {"items": [{"student_id": str(uuid4()), "status_code": "present"}]}
    )
    second = AttendanceMarkRequest.model_validate(
        {"items": [{"student_id": str(uuid4()), "status_code": "present"}]}
    )
    assert request_fingerprint(first) != request_fingerprint(second)
