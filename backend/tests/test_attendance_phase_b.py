from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.modules.attendance.schemas import AttendanceMarkRequest
from app.modules.attendance.service import _resolve_status_and_lateness


class DummyCursor:
    pass


def test_mark_request_rejects_duplicate_students():
    student_id = uuid4()
    with pytest.raises(ValueError, match="only appear once"):
        AttendanceMarkRequest.model_validate(
            {
                "items": [
                    {"student_id": str(student_id), "status_code": "present"},
                    {"student_id": str(student_id), "status_code": "absent"},
                ]
            }
        )


@pytest.mark.asyncio
async def test_present_is_evaluated_as_late_after_grace(monkeypatch):
    import app.modules.attendance.service as service

    status_present = (uuid4(), "present", "Present", None, "attendance", 1, 1, 10)
    status_late = (uuid4(), "late", "Late", None, "exception", 1, 1, 20)

    async def fake_status(cur, tenant_id, code):
        return status_present if code == "present" else status_late

    async def fake_policy(cur, tenant_id, session_date):
        return (uuid4(), 10)

    monkeypatch.setattr(service, "get_status", fake_status)
    monkeypatch.setattr(service, "get_policy", fake_policy)

    session = [None, None, None, None, None, None, "lesson", datetime(2026, 9, 10).date(), datetime(2026, 9, 10, 8, 0), None]
    item = SimpleNamespace(status_code="present", marked_at=datetime(2026, 9, 10, 8, 16))

    status, marked_at, late_minutes = await _resolve_status_and_lateness(DummyCursor(), uuid4(), session, item, "manual")

    assert status[1] == "late"
    assert late_minutes == 16
    assert marked_at == item.marked_at


@pytest.mark.asyncio
async def test_present_within_grace_remains_present(monkeypatch):
    import app.modules.attendance.service as service

    status_present = (uuid4(), "present", "Present", None, "attendance", 1, 1, 10)

    async def fake_status(cur, tenant_id, code):
        return status_present

    async def fake_policy(cur, tenant_id, session_date):
        return (uuid4(), 15)

    monkeypatch.setattr(service, "get_status", fake_status)
    monkeypatch.setattr(service, "get_policy", fake_policy)

    session = [None, None, None, None, None, None, "lesson", datetime(2026, 9, 10).date(), datetime(2026, 9, 10, 8, 0), None]
    item = SimpleNamespace(status_code="present", marked_at=datetime(2026, 9, 10, 8, 15))

    status, _, late_minutes = await _resolve_status_and_lateness(DummyCursor(), uuid4(), session, item, "manual")

    assert status[1] == "present"
    assert late_minutes is None
