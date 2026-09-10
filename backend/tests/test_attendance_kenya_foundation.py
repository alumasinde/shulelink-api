from datetime import time

from app.modules.attendance.domain.session_types import DEFAULTS, applies_to_residency


def test_dormitory_session_is_boarder_only():
    assert applies_to_residency("dormitory_night_check", "boarder")
    assert not applies_to_residency("dormitory_night_check", "day_scholar")


def test_daily_roll_calls_apply_to_all_residencies():
    assert applies_to_residency("morning_roll_call", "day_scholar")
    assert applies_to_residency("morning_roll_call", "boarder")
    assert DEFAULTS["morning_roll_call"][0] == time(7, 0)


def test_unknown_session_type_has_no_forced_residency_rule():
    assert applies_to_residency("lesson", "day_scholar")
    assert applies_to_residency("lesson", "boarder")
