from fastapi import HTTPException
import pytest
from app.modules.curriculum.schemas import CurriculumTemplateDocument, CurriculumLevel, CurriculumGrade, CurriculumSubject, CurriculumLearningArea, CurriculumOffering, CurriculumCombination
from app.modules.curriculum.service import _validate


def base_document():
    return CurriculumTemplateDocument(
        levels=[CurriculumLevel(code='senior_school', name='Senior School')],
        grades=[CurriculumGrade(code='grade_10', name='Grade 10', education_level_code='senior_school')],
        learning_areas=[CurriculumLearningArea(code='stem', name='STEM')],
        subjects=[CurriculumSubject(code='biology', name='Biology', learning_area_code='stem')],
    )


def test_curriculum_document_accepts_dynamic_structure():
    _validate(base_document())


def test_curriculum_document_rejects_unknown_grade_reference():
    doc=base_document()
    doc.offerings=[CurriculumOffering(grade_code='grade_99', subject_code='biology')]
    with pytest.raises(HTTPException): _validate(doc)


def test_curriculum_document_rejects_unknown_combination_subject():
    doc=base_document()
    doc.combinations=[CurriculumCombination(code='stem_a', name='STEM A', subjects=['chemistry'])]
    with pytest.raises(HTTPException): _validate(doc)
