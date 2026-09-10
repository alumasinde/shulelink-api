from uuid import uuid4
from app.modules.academics.schemas import TeacherCreate, TeacherUpdate, GenerateRequest
from app.modules.school_structure.schemas import SubjectCreate, ClassSubjectCreate, TermCreate


def test_teacher_subject_eligibility_is_not_limited_to_two():
    ids = [uuid4() for _ in range(6)]
    teacher = TeacherCreate(teacher_number='T-100', first_name='A', last_name='Teacher', subject_ids=ids)
    assert teacher.subject_ids == ids


def test_teacher_department_is_not_required_for_subject_eligibility():
    teacher = TeacherCreate(teacher_number='T-101', first_name='A', last_name='Teacher', subject_ids=[uuid4(), uuid4(), uuid4()])
    assert teacher.department_id is None
    assert len(teacher.subject_ids) == 3


def test_teacher_status_and_gender_are_dynamic_strings():
    teacher = TeacherCreate(teacher_number='T-102', first_name='A', last_name='Teacher', gender='female_staff', status='sabbatical')
    updated = TeacherUpdate(gender='custom_gender', status='custom_status')
    assert teacher.gender == 'female_staff'
    assert teacher.status == 'sabbatical'
    assert updated.gender == 'custom_gender'


def test_subject_type_and_class_requirement_are_dynamic():
    subject = SubjectCreate(code='ENV', name='Environmental Learning', subject_type='school_defined')
    offering = ClassSubjectCreate(class_level_id=uuid4(), subject_id=uuid4(), requirement_type='school_option', weekly_periods=4)
    assert subject.subject_type == 'school_defined'
    assert offering.requirement_type == 'school_option'
    assert offering.weekly_periods == 4


def test_term_count_is_not_locked_to_four():
    term = TermCreate(academic_year_id=uuid4(), name='Term 5', term_number=5, start_date='2026-09-01', end_date='2026-10-01')
    assert term.term_number == 5


def test_timetable_generation_lesson_count_can_be_platform_resolved():
    request = GenerateRequest(academic_year_id=uuid4(), academic_term_id=uuid4(), lessons_per_week=None)
    assert request.lessons_per_week is None
