"""tests/test_classifier.py — Unit tests for classifier/intake.py.

All tests are deterministic (no real LLM calls). Tests verify:
- Empty description → out_of_scope
- No API key → out_of_scope
- Classifier never raises; always returns ClassifierResult
- ClassifierResult Pydantic model rejects invalid categories
- API key absent: fallback is correct category and confidence
"""
from __future__ import annotations
import pytest
from classifier.intake import classify_project, ClassifierResult


def test_empty_description_is_out_of_scope():
    """Empty description must default to out_of_scope (spec: require geometry + description for number)."""
    result = classify_project(description="", permit_type="HTI")
    assert result.category == "out_of_scope"
    assert result.confidence == "low"


def test_whitespace_description_is_out_of_scope():
    """Whitespace-only description must default to out_of_scope."""
    result = classify_project(description="   \n\t  ", permit_type="HA")
    assert result.category == "out_of_scope"


def test_no_api_key_falls_back_to_out_of_scope(monkeypatch):
    """No ANTHROPIC_API_KEY → out_of_scope fallback (never raises)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = classify_project(description="HTI plantation forest concession in East Kalimantan", permit_type="HTI")
    assert result.category == "out_of_scope"
    assert result.confidence == "low"
    assert result.rationale  # non-empty explanation


def test_classifier_result_valid_categories():
    """ClassifierResult accepts all four valid category literals."""
    for cat in ("REDD", "IFM", "PEAT", "out_of_scope"):
        r = ClassifierResult(category=cat)
        assert r.category == cat


def test_classifier_result_rejects_invalid_category():
    """ClassifierResult must reject unknown categories via Pydantic validation."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ClassifierResult(category="EUDR")


def test_classifier_result_defaults():
    """ClassifierResult has sensible defaults for optional fields."""
    r = ClassifierResult(category="out_of_scope")
    assert r.confidence == "low"
    assert r.structured_facts == {}
    assert r.rationale == ""
    assert r.out_of_scope_reason == ""


def test_classifier_never_raises_on_any_input(monkeypatch):
    """Classifier must never raise an exception for any input — always returns ClassifierResult."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    for desc in [
        "agricultural land",
        "This is a 100,000 ha carbon project that will generate 50M credits per year",
        "x" * 3000,  # very long input
        "!@#$%^&*()",
    ]:
        result = classify_project(description=desc, permit_type="HTI")
        assert isinstance(result, ClassifierResult), f"Expected ClassifierResult, got {type(result)}"
        assert result.category in ("REDD", "IFM", "PEAT", "out_of_scope")
