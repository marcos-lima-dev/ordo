import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import MagicMock

import pytest

import pipeline.query_resolution_pipeline as qrp
from pipeline.query_resolution_pipeline import resolve_query
from pipeline.semantic_intent_router import (
    SemanticIntent,
    MessageCategory,
    categorize,
)
from order.query_resolution_result import (
    QueryResolutionResult,
    QueryResolutionStatus,
)
from order.resolved_query import QueryType, ResolvedQuery
from order.query_boundary import to_resolved_query

_MODULE_PATH = (
    Path(__file__).parent.parent / "pipeline" / "query_resolution_pipeline.py"
)


@pytest.fixture(scope="module")
def module_source():
    return _MODULE_PATH.read_text(encoding="utf-8")


# =============================================
# Autouse — never trigger real instantiation
# =============================================

@pytest.fixture(autouse=True)
def safe_default_stubs(monkeypatch):
    """
    Prevent any test from triggering real ModularAdapter / CatalogRetriever
    / ProductResolver instantiation. Individual tests override as needed.
    """
    a = MagicMock()
    a.predict.return_value = {
        "product_term": None,
        "explicit_brand": None,
        "explicit_presentation": None,
        "intent": "UNKNOWN",
    }
    monkeypatch.setattr(qrp, "_adapter", a)

    r = MagicMock()
    r.retrieve_with_provenance.return_value = ([], {})
    monkeypatch.setattr(qrp, "_catalog_retriever", r)

    p = MagicMock()
    p.resolve.return_value = "NOT_FOUND"
    monkeypatch.setattr(qrp, "_product_resolver", p)


# =============================================
# Stub installer
# =============================================

_STANDARD_INTERPRETATION = {
    "product_term": "provolone Tânia",
    "explicit_brand": "Tânia",
    "explicit_presentation": None,
    "intent": "UNKNOWN",  # ignored by resolve_query
}


def _install(
    monkeypatch,
    *,
    interpretation=None,
    candidates=None,
    provenance=None,
    product_status="NOT_FOUND",
):
    interp = (
        dict(_STANDARD_INTERPRETATION)
        if interpretation is None
        else interpretation
    )
    cands = candidates if candidates is not None else []
    prov = provenance if provenance is not None else {}

    a = MagicMock()
    a.predict.return_value = interp
    monkeypatch.setattr(qrp, "_adapter", a)

    r = MagicMock()
    r.retrieve_with_provenance.return_value = (cands, prov)
    monkeypatch.setattr(qrp, "_catalog_retriever", r)

    p = MagicMock()
    p.resolve.return_value = product_status
    monkeypatch.setattr(qrp, "_product_resolver", p)

    return a, r, p


# =============================================
# QP-01 — QUERY_PRICE + resolvable product → RESOLVED
# =============================================

def test_qp01_query_price_resolved(monkeypatch):
    _install(
        monkeypatch,
        candidates=["CQ-44"],
        provenance={"CQ-44": "ORIGINAL_ALIAS_EXACT"},
        product_status="EXACT_MATCH",
    )
    result = resolve_query(
        "quanto tá o provolone Tânia?", SemanticIntent.QUERY_PRICE
    )
    assert isinstance(result, QueryResolutionResult)
    assert result.status is QueryResolutionStatus.RESOLVED
    assert result.query_type is QueryType.QUERY_PRICE
    assert result.product_id == "CQ-44"
    assert result.reason_code is None


# =============================================
# QP-02 — QUERY_AVAILABILITY + resolvable product → RESOLVED
# =============================================

def test_qp02_query_availability_resolved(monkeypatch):
    _install(
        monkeypatch,
        candidates=["CQ-44"],
        provenance={"CQ-44": "ORIGINAL_ALIAS_EXACT"},
        product_status="EXACT_MATCH",
    )
    result = resolve_query(
        "tem provolone Tânia?", SemanticIntent.QUERY_AVAILABILITY
    )
    assert result.status is QueryResolutionStatus.RESOLVED
    assert result.query_type is QueryType.QUERY_AVAILABILITY
    assert result.product_id == "CQ-44"


# =============================================
# QP-03 — ambiguous product → NEEDS_CLARIFICATION
# =============================================

def test_qp03_ambiguous_returns_needs_clarification(monkeypatch):
    _install(
        monkeypatch,
        candidates=["CQ-44", "CQ-46"],
        provenance={
            "CQ-44": "ORIGINAL_ALIAS_TOKEN",
            "CQ-46": "ORIGINAL_ALIAS_TOKEN",
        },
        product_status="AMBIGUOUS",
    )
    result = resolve_query(
        "quanto tá o provolone?", SemanticIntent.QUERY_PRICE
    )
    assert result.status is QueryResolutionStatus.NEEDS_CLARIFICATION
    assert result.product_id is None
    assert result.reason_code == "AMBIGUOUS_PRODUCT"


# =============================================
# QP-04 — nonexistent product → PRODUCT_NOT_FOUND
# =============================================

def test_qp04_not_found_returns_product_not_found(monkeypatch):
    _install(
        monkeypatch,
        candidates=[],
        provenance={},
        product_status="NOT_FOUND",
    )
    result = resolve_query(
        "quanto tá o queijo xyz inexistente?", SemanticIntent.QUERY_PRICE
    )
    assert result.status is QueryResolutionStatus.PRODUCT_NOT_FOUND
    assert result.product_id is None
    assert result.reason_code == "PRODUCT_NOT_FOUND"


# =============================================
# QP-05 / QP-06 — boundary produces valid ResolvedQuery
# =============================================

def test_qp05_resolved_price_boundary_produces_valid_resolved_query(monkeypatch):
    _install(
        monkeypatch,
        candidates=["CQ-44"],
        provenance={"CQ-44": "ORIGINAL_ALIAS_EXACT"},
        product_status="EXACT_MATCH",
    )
    result = resolve_query("...", SemanticIntent.QUERY_PRICE)
    rq = to_resolved_query(result)
    assert rq is not None
    assert isinstance(rq, ResolvedQuery)
    assert rq.is_valid() is True
    assert rq.product_id == "CQ-44"
    assert rq.query_type is QueryType.QUERY_PRICE


def test_qp06_resolved_availability_boundary_produces_valid_resolved_query(monkeypatch):
    _install(
        monkeypatch,
        candidates=["CQ-28"],
        provenance={"CQ-28": "ORIGINAL_ALIAS_EXACT"},
        product_status="EXACT_MATCH",
    )
    result = resolve_query("...", SemanticIntent.QUERY_AVAILABILITY)
    rq = to_resolved_query(result)
    assert rq is not None
    assert rq.is_valid() is True
    assert rq.query_type is QueryType.QUERY_AVAILABILITY


# =============================================
# QP-07 / QP-08 — boundary returns None
# =============================================

def test_qp07_ambiguous_boundary_returns_none(monkeypatch):
    _install(
        monkeypatch,
        candidates=["CQ-44", "CQ-46"],
        provenance={"CQ-44": "ORIGINAL_ALIAS_TOKEN", "CQ-46": "ORIGINAL_ALIAS_TOKEN"},
        product_status="AMBIGUOUS",
    )
    result = resolve_query("...", SemanticIntent.QUERY_PRICE)
    assert to_resolved_query(result) is None


def test_qp08_not_found_boundary_returns_none(monkeypatch):
    _install(
        monkeypatch,
        candidates=[],
        provenance={},
        product_status="NOT_FOUND",
    )
    result = resolve_query("...", SemanticIntent.QUERY_PRICE)
    assert to_resolved_query(result) is None


# =============================================
# QP-09 / QP-10 — adapter intent cannot override semantic_intent
# =============================================

def test_qp09_adapter_command_intent_cannot_override_query_price(monkeypatch):
    interp = dict(_STANDARD_INTERPRETATION)
    interp["intent"] = "ADD_ITEM"  # adapter says COMMAND
    _install(
        monkeypatch,
        interpretation=interp,
        candidates=["CQ-44"],
        provenance={"CQ-44": "ORIGINAL_ALIAS_EXACT"},
        product_status="EXACT_MATCH",
    )
    result = resolve_query("...", SemanticIntent.QUERY_PRICE)
    assert result.query_type is QueryType.QUERY_PRICE
    assert result.status is QueryResolutionStatus.RESOLVED


def test_qp10_adapter_unknown_intent_cannot_override_query_availability(monkeypatch):
    interp = dict(_STANDARD_INTERPRETATION)
    interp["intent"] = "UNKNOWN"  # adapter says UNKNOWN
    _install(
        monkeypatch,
        interpretation=interp,
        candidates=["CQ-28"],
        provenance={"CQ-28": "ORIGINAL_ALIAS_EXACT"},
        product_status="EXACT_MATCH",
    )
    result = resolve_query("...", SemanticIntent.QUERY_AVAILABILITY)
    assert result.query_type is QueryType.QUERY_AVAILABILITY
    assert result.status is QueryResolutionStatus.RESOLVED


# =============================================
# QP-11 / QP-12 — no state, no engine (structural)
# =============================================

def test_qp11_module_does_not_import_order_state(module_source):
    import_re = re.compile(
        r"^\s*(?:from\s+order\.state\s+import|import\s+order\.state)",
        re.MULTILINE,
    )
    assert not import_re.search(module_source)


def test_qp12_module_does_not_import_order_engine(module_source):
    import_re = re.compile(
        r"^\s*(?:from\s+order\.engine\s+import|import\s+order\.engine)",
        re.MULTILINE,
    )
    assert not import_re.search(module_source)


def test_qp12b_module_does_not_import_pending_resolver(module_source):
    import_re = re.compile(
        r"^\s*(?:from\s+order\.pending_resolver\s+import|import\s+order\.pending_resolver)",
        re.MULTILINE,
    )
    assert not import_re.search(module_source)


def test_qp12c_module_does_not_import_execution(module_source):
    import_re = re.compile(
        r"^\s*(?:from\s+order\.execution\s+import|import\s+order\.execution)",
        re.MULTILINE,
    )
    assert not import_re.search(module_source)


# =============================================
# QP-13 — deterministic
# =============================================

def test_qp13_deterministic_same_input(monkeypatch):
    _install(
        monkeypatch,
        candidates=["CQ-44"],
        provenance={"CQ-44": "ORIGINAL_ALIAS_EXACT"},
        product_status="EXACT_MATCH",
    )
    r1 = resolve_query("quanto tá o provolone Tânia?", SemanticIntent.QUERY_PRICE)
    r2 = resolve_query("quanto tá o provolone Tânia?", SemanticIntent.QUERY_PRICE)
    assert r1.status is r2.status
    assert r1.query_type is r2.query_type
    assert r1.product_id == r2.product_id
    assert r1.reason_code == r2.reason_code
    assert r1.evidence == r2.evidence


# =============================================
# QP-14 — inputs not mutated
# =============================================

def test_qp14_semantic_intent_not_mutated(monkeypatch):
    _install(
        monkeypatch,
        candidates=["CQ-44"],
        provenance={"CQ-44": "ORIGINAL_ALIAS_EXACT"},
        product_status="EXACT_MATCH",
    )
    intent = SemanticIntent.QUERY_PRICE
    _ = resolve_query("...", intent)
    assert intent is SemanticIntent.QUERY_PRICE


def test_qp14b_interpretation_dict_not_mutated(monkeypatch):
    interp = dict(_STANDARD_INTERPRETATION)
    snapshot = dict(interp)
    _install(
        monkeypatch,
        interpretation=interp,
        candidates=["CQ-44"],
        provenance={"CQ-44": "ORIGINAL_ALIAS_EXACT"},
        product_status="EXACT_MATCH",
    )
    _ = resolve_query("...", SemanticIntent.QUERY_PRICE)
    assert interp == snapshot


# =============================================
# QP-15 — evidence contains only real resolution evidence
# =============================================

def test_qp15_evidence_is_real_provenance_for_resolved(monkeypatch):
    _install(
        monkeypatch,
        candidates=["CQ-44"],
        provenance={"CQ-44": "ORIGINAL_ALIAS_EXACT"},
        product_status="EXACT_MATCH",
    )
    result = resolve_query("...", SemanticIntent.QUERY_PRICE)
    assert result.evidence == ["CQ-44:ORIGINAL_ALIAS_EXACT"]


def test_qp15b_evidence_covers_all_candidates_for_ambiguous(monkeypatch):
    _install(
        monkeypatch,
        candidates=["CQ-44", "CQ-46"],
        provenance={
            "CQ-44": "ORIGINAL_ALIAS_TOKEN",
            "CQ-46": "ORIGINAL_ALIAS_TOKEN",
        },
        product_status="AMBIGUOUS",
    )
    result = resolve_query("...", SemanticIntent.QUERY_PRICE)
    assert result.evidence == [
        "CQ-44:ORIGINAL_ALIAS_TOKEN",
        "CQ-46:ORIGINAL_ALIAS_TOKEN",
    ]


# =============================================
# QP-16 — boundary still does not propagate evidence
# =============================================

def test_qp16_boundary_does_not_propagate_evidence(monkeypatch):
    _install(
        monkeypatch,
        candidates=["CQ-44"],
        provenance={"CQ-44": "ORIGINAL_ALIAS_EXACT"},
        product_status="EXACT_MATCH",
    )
    result = resolve_query("...", SemanticIntent.QUERY_PRICE)
    # QueryResolutionResult carries real evidence:
    assert result.evidence == ["CQ-44:ORIGINAL_ALIAS_EXACT"]
    # Boundary does NOT propagate it (Stage 3 decision):
    rq = to_resolved_query(result)
    assert rq is not None
    assert rq.evidence == []


# =============================================
# QP-17 / QP-18 — API misuse
# =============================================

def test_qp17_add_item_raises_value_error(monkeypatch):
    with pytest.raises(ValueError, match="requires a QUERY semantic intent"):
        resolve_query("quero provolone", SemanticIntent.ADD_ITEM)


def test_qp18_unknown_raises_value_error(monkeypatch):
    with pytest.raises(ValueError, match="requires a QUERY semantic intent"):
        resolve_query("qualquer coisa", SemanticIntent.UNKNOWN)


_NON_QUERY_INTENTS = [
    SemanticIntent.ADD_ITEM,
    SemanticIntent.REMOVE_ITEM,
    SemanticIntent.CHANGE_QUANTITY,
    SemanticIntent.REPLACE_ITEM,
    SemanticIntent.CONFIRM_ORDER,
    SemanticIntent.CANCEL_ORDER,
    SemanticIntent.UNKNOWN,
]


@pytest.mark.parametrize("intent", _NON_QUERY_INTENTS)
def test_all_non_query_intents_raise_value_error(intent):
    with pytest.raises(ValueError, match="requires a QUERY semantic intent"):
        resolve_query("any message", intent)


def test_property_non_query_categorization_implies_value_error():
    """
    ∀ intent: categorize(intent) != QUERY → resolve_query raises ValueError.
    """
    for intent in SemanticIntent:
        if categorize(intent) is not MessageCategory.QUERY:
            with pytest.raises(ValueError):
                resolve_query("any", intent)


def test_misuse_does_not_call_adapter(monkeypatch):
    """Precondition is checked before the adapter is invoked."""
    a = MagicMock()
    monkeypatch.setattr(qrp, "_adapter", a)
    with pytest.raises(ValueError):
        resolve_query("...", SemanticIntent.ADD_ITEM)
    a.predict.assert_not_called()


# =============================================
# HIGH_CONFIDENCE — STOP path
# =============================================

def test_high_confidence_raises_runtime_error(monkeypatch):
    """
    HIGH_CONFIDENCE is NOT AUTHORIZED in Stage 4C. If observed, the
    implementation must raise — no silent mapping.
    """
    _install(
        monkeypatch,
        candidates=["CQ-44"],
        provenance={"CQ-44": "ORIGINAL_ALIAS_EXACT"},
        product_status="HIGH_CONFIDENCE",
    )
    with pytest.raises(RuntimeError, match="HIGH_CONFIDENCE"):
        resolve_query("...", SemanticIntent.QUERY_PRICE)