from datetime import time


DEFAULTS = {
    "morning_roll_call": (time(7, 0), time(9, 0), "all"),
    "afternoon_roll_call": (time(13, 0), time(15, 30), "all"),
    "dormitory_night_check": (time(19, 0), time(23, 0), "boarder"),
}


def applies_to_residency(session_type: str, residency_type: str) -> bool:
    default = DEFAULTS.get(session_type)
    return default is None or default[2] == "all" or default[2] == residency_type
