from datetime import time
from uuid import uuid4
import pytest
from pydantic import ValidationError
from app.modules.academics.schemas import PeriodCreate, TimetableCreate, GenerateRequest, TeacherCreate


def test_teacher_requires_names_and_valid_gender():
    t=TeacherCreate(teacher_number='T-001',first_name='Jane',last_name='Doe')
    assert t.gender=='unspecified'
    with pytest.raises(ValidationError): TeacherCreate(teacher_number='T-001',first_name='Jane',last_name='Doe',gender='invalid')


def test_period_rejects_reversed_times():
    with pytest.raises(ValidationError): PeriodCreate(code='P1',name='Period 1',start_time=time(10),end_time=time(9),sort_order=1)


def test_timetable_day_is_bounded():
    base=dict(academic_year_id=uuid4(),academic_term_id=uuid4(),class_level_id=uuid4(),subject_id=uuid4(),teacher_id=uuid4(),period_id=uuid4(),day_of_week=1)
    assert TimetableCreate(**base).day_of_week==1
    with pytest.raises(ValidationError): TimetableCreate(**{**base,'day_of_week':0})
    with pytest.raises(ValidationError): TimetableCreate(**{**base,'day_of_week':8})


def test_generator_has_safe_lesson_bounds():
    req=GenerateRequest(academic_year_id=uuid4(),academic_term_id=uuid4(),lessons_per_week=7)
    assert req.lessons_per_week==7
    with pytest.raises(ValidationError): GenerateRequest(academic_year_id=uuid4(),academic_term_id=uuid4(),lessons_per_week=0)
    with pytest.raises(ValidationError): GenerateRequest(academic_year_id=uuid4(),academic_term_id=uuid4(),lessons_per_week=11)
