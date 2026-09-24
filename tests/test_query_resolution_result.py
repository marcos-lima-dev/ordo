import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from order.query_resolution_result import (
    QueryResolutionResult,
    QueryResolutionStatus,
)
from order.resolved_query import QueryType
from order.resolution_result import OutcomeType

_MODULE_PATH = Path(__file__).parent.parent / "order" / "query_resolution_result.py"


@pytest.fixture(scope="module")
def result_source():
    return _MODULE_PATH.read_text(encoding="utf-8")


# =============================================
# Status representation
# =============================================

def test_can_represent_resolved():
    r = QueryResolutionResult(
        status=QueryResolutionStatus.RESOLVED,
        query_type=QueryType.QUERY_PRICE,
        product_id="CQ-44",
    )
    assert r.status is QueryResolutionStatus.RESOLVED
    assert r.product_id == "CQ-44"


def test_can_represent_needs_clarification_without_orderstate():
    """NEEDS_CLARIFICATION must be representable without touching OrderState."""
    r = QueryResolutionResult(
        status=QueryResolutionStatus.NEEDS_CLARIFICATION,
        query_type=QueryType.QUERY_PRICE,
        reason_code="AMBIGUOUS_PRODUCT",
    )
    assert r.status is QueryResolutionStatus.NEEDS_CLARIFICATION
    assert r.product_id is None
    assert r.reason_code == "AMBIGUOUS_PRODUCT"


def test_can_represent_product_not_found():
    r = QueryResolutionResult(
        status=QueryResolutionStatus.PRODUCT_NOT_FOUND,
        query_type=QueryType.QUERY_AVAILABILITY,
        reason_code="PRODUCT_NOT_FOUND",
    )
    assert r.status is QueryResolutionStatus.PRODUCT_NOT_FOUND


# =============================================
# BLOCKED not added (no speculative states)
# =============================================

def test_blocked_is_not_a_status_member():
    members = {s.name for s in QueryResolutionStatus}
    assert "BLOCKED" not in members


# =============================================
# OutcomeType not extended with QUERY (T10-P4)
# =============================================

def test_outcome_type_not_extended_with_query():
    member_names = {o.name for o in OutcomeType}
    assert "QUERY" not in member_names


# =============================================
# INVARIANT — no dependency on command engine / OrderState
# (checks imports, not mentions in comments/docstrings)
# =============================================

def test_result_module_does_not_import_order_engine(result_source):
    import_re = re.compile(
        r"^\s*(?:from\s+order\.engine\s+import|import\s+order\.engine)",
        re.MULTILINE,
    )
    assert not import_re.search(result_source), (
        "query_resolution_result.py must not import order.engine (T10-P3)."
    )


def test_result_module_does_not_import_order_state(result_source):
    import_re = re.compile(
        r"^\s*(?:from\s+order\.state\s+import|import\s+order\.state)",
        re.MULTILINE,
    )
    assert not import_re.search(result_source), (
        "query_resolution_result.py must not import order.state (T10-P3)."
    )


def test_result_module_does_not_import_operation_fields(result_source):
    """No dependency on order.operation_fields (T10-P4)."""
    import_re = re.compile(
        r"^\s*(?:from\s+order\.operation_fields\s+import|import\s+order\.operation_fields)",
        re.MULTILINE,
    )
    assert not import_re.search(result_source), (
        "query_resolution_result.py must not import order.operation_fields (T10-P4)."
    )


# =============================================
# evidence default
# =============================================

def test_evidence_defaults_to_empty_list():
    r = QueryResolutionResult(
        status=QueryResolutionStatus.RESOLVED,
        query_type=QueryType.QUERY_PRICE,
        product_id="CQ-44",
    )
    assert r.evidence == []