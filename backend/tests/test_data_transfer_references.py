from app.modules.data_transfer.routes.v1.data_transfer import (
    _reference_candidates,
    _reference_key,
    _resolve_reference,
)


def test_reference_key_normalizes_case_and_whitespace():
    assert _reference_key("  Grade   5 ") == "grade 5"
    assert _reference_key("G5") == "g5"


def test_class_level_resolves_by_name_or_code():
    rows = [("class-5", "G5", "Grade 5"), ("class-6", "G6", "Grade 6")]
    lookup, ambiguous = _reference_candidates(rows)

    assert _resolve_reference("Grade 5", lookup, ambiguous, "Class level", ["Grade 5", "Grade 6"]) == "class-5"
    assert _resolve_reference("g5", lookup, ambiguous, "Class level", ["Grade 5", "Grade 6"]) == "class-5"


def test_stream_resolves_stream_prefix():
    rows = [("stream-a", "A", "Stream A"), ("stream-b", "B", "Stream B")]
    lookup, ambiguous = _reference_candidates(rows)

    assert _resolve_reference("A", lookup, ambiguous, "Stream", ["Stream A", "Stream B"]) == "stream-a"
    assert _resolve_reference(" stream A ", lookup, ambiguous, "Stream", ["Stream A", "Stream B"]) == "stream-a"


def test_reference_candidates_detects_ambiguous_aliases():
    rows = [("class-1", "G1", "Grade 1"), ("class-2", "G2", "G1")]
    lookup, ambiguous = _reference_candidates(rows)

    assert "g1" in ambiguous
    assert "g1" not in lookup
