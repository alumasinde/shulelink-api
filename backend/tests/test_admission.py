from datetime import date

from app.modules.students.admission import format_admission_number


def test_admission_number_full_format():
    assert format_admission_number("ADM", "-", True, "YYYY", 1, 4, date(2026, 1, 5)) == "ADM-2026-0001"


def test_admission_number_without_year():
    assert format_admission_number("SCH", "/", False, "YYYY", 42, 3, date(2026, 1, 5)) == "SCH/042"


def test_admission_number_two_digit_year():
    assert format_admission_number("", "", True, "YY", 7, 2, date(2026, 1, 5)) == "2607"
