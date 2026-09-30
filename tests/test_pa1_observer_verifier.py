"""
Tests for PA-1 Observer and Verifier.

Contract: PA1 Explicit Identifier Input Contract v0
Rule:     PA1 Acceptance Rule Design v0
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import inspect
import pytest

from pipeline.pa1_observer import observe, PA1Observation, PA1Occurrence
from pipeline.pa1_verifier import verify, verify_all, EXISTS, NOT_EXISTS, UNVERIFIABLE


# ============================================
# Positive recognition — MUST support
# ============================================

@pytest.mark.parametrize("message,expected_raw", [
    ("manda o CQ-44",       "CQ-44"),
    ("manda o cq-44",       "cq-44"),
    ("manda o CQ44",        "CQ44"),
    ("manda o CQ 44",       "CQ 44"),
    ("manda o CQ-99",       "CQ-99"),
])
def test_positive_recognition(message, expected_raw):
    obs = observe(message)
    assert obs.presence == "PRESENT"
    assert len(obs.occurrences) == 1
    assert obs.occurrences[0].raw == expected_raw


# ============================================
# Negative recognition — MUST reject
# ============================================

@pytest.mark.parametrize("message", [
    "manda o 44",
    "manda o CQ",
    "aquele CQ que falamos",
    "manda o CQ44ok",
    "manda o CQ-999",
])
def test_negative_recognition(message):
    obs = observe(message)
    assert obs.presence == "ABSENT"
    assert obs.occurrences == ()


# ============================================
# Verification — EXISTS / NOT_EXISTS / UNVERIFIABLE
# ============================================

def test_verification_exists():
    v = verify("CQ-44")
    assert v.status == EXISTS


def test_verification_not_exists():
    v = verify("CQ-99")
    assert v.status == NOT_EXISTS


@pytest.mark.parametrize("raw", ["CQ-99", "cq-99", "CQ99", "CQ 99"])
def test_verification_not_exists_representation_variants(raw):
    """All accepted forms of CQ-99 share the same lookup key."""
    v = verify(raw)
    assert v.status == NOT_EXISTS


def test_verification_unverifiable_when_catalog_fails():
    import pipeline.pa1_verifier as mod

    class BrokenCatalog:
        @property
        def catalog(self):
            raise RuntimeError("boom")

    v = mod.verify("CQ-44", catalog=BrokenCatalog())
    assert v.status == UNVERIFIABLE


# ============================================
# Preservation — raw / span / provenance / multiplicity
# ============================================

def test_raw_preserved_exactly():
    msg = "manda o cq-44 por favor"
    obs = observe(msg)
    assert obs.occurrences[0].raw == "cq-44"


def test_span_correct():
    msg = "manda o CQ-44"
    obs = observe(msg)
    start, end = obs.occurrences[0].span
    assert msg[start:end] == "CQ-44"


def test_provenance_present():
    obs = observe("manda o CQ-44")
    assert isinstance(obs.occurrences[0].recognition_provenance, str)
    assert obs.occurrences[0].recognition_provenance != ""


def test_multiplicity_preserved():
    msg = "manda CQ-44 e CQ-46"
    obs = observe(msg)
    assert obs.presence == "PRESENT"
    assert len(obs.occurrences) == 2
    assert {o.raw for o in obs.occurrences} == {"CQ-44", "CQ-46"}


def test_multiplicity_does_not_collapse_duplicates():
    msg = "CQ-44 e de novo CQ-44"
    obs = observe(msg)
    assert len(obs.occurrences) == 2


# ============================================
# Isolation — Observer imports are minimal
# ============================================

def test_observer_module_does_not_reference_retrieval():
    import pipeline.pa1_observer as mod
    source = inspect.getsource(mod)
    forbidden = [
        "CatalogRetriever",
        "ProductResolver",
        "normalize_query",
        "retrieve_with_provenance",
        "resolve_operation",
    ]
    for name in forbidden:
        assert name not in source, f"observer must not reference {name}"


def test_verifier_module_does_not_reference_semantic_retrieval():
    import pipeline.pa1_verifier as mod
    source = inspect.getsource(mod)
    forbidden = [
        "retrieve_with_provenance",
        "retrieve_with_constraints",
        "normalize_query",
    ]
    for name in forbidden:
        assert name not in source, f"verifier must not reference {name}"


# ============================================
# Regression — commercial behavior unchanged
# ============================================

def test_resolve_operation_not_affected_by_pa1_modules():
    """
    PA-1 is observed capability, not authority. Running resolve_operation on
    a message containing CQ-XX must remain equivalent to the pre-PA-1 baseline.
    This test only asserts the pipeline does not blow up and does not consume
    PA-1 — regression coverage for commercial behavior lives in the existing suite.
    """
    from order.state import OrderState
    from pipeline.resolution_pipeline import resolve_operation

    result = resolve_operation("manda o CQ-44", OrderState())
    assert result is not None