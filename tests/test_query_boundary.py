import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from order.query_resolution_result import (
    QueryResolutionResult,
    QueryResolutionStatus,
)
from order.resolved_query import QueryType, ResolvedQuery
from order.query_boundary import to_resolved_query

_MODULE_PATH = Path(__file__).parent.parent / "order" / "query_boundary.py"


@pytest.fixture(scope="module")
def boundary_source():
    return _MODULE_PATH.read_text(encoding="utf-8")


# =============================================
# QB-01 — PRICE happy path
# =============================================

def test_qb01_resolved_price_query_maps_to_resolved_query():
    result = QueryResolutionResult(
        status=QueryResolutionStatus.RESOLVED,
        query_type=QueryType.QUERY_PRICE,
        product_id="CQ-44",
    )
    rq = to_resolved_query(result)
    assert rq is not None
    assert isinstance(rq, ResolvedQuery)
    assert rq.query_type is QueryType.QUERY_PRICE
    assert rq.product_id == "CQ-44"
    assert rq.is_valid() is True


# =============================================
# QB-02 — AVAILABILITY happy path
# =============================================

def test_qb02_resolved_availability_query_maps_to_resolved_query():
    result = QueryResolutionResult(
        status=QueryResolutionStatus.RESOLVED,
        query_type=QueryType.QUERY_AVAILABILITY,
        product_id="CQ-28",
    )
    rq = to_resolved_query(result)
    assert rq is not None
    assert rq.query_type is QueryType.QUERY_AVAILABILITY
    assert rq.product_id == "CQ-28"
    assert rq.is_valid() is True


# =============================================
# QB-03 — missing product_id
# =============================================

def test_qb03_resolved_without_product_id_does_not_cross_boundary():
    result = QueryResolutionResult(
        status=QueryResolutionStatus.RESOLVED,
        query_type=QueryType.QUERY_PRICE,
        product_id=None,
    )
    assert to_resolved_query(result) is None


# =============================================
# QB-04 — NEEDS_CLARIFICATION
# =============================================

def test_qb04_needs_clarification_does_not_cross_boundary():
    result = QueryResolutionResult(
        status=QueryResolutionStatus.NEEDS_CLARIFICATION,
        query_type=QueryType.QUERY_PRICE,
        reason_code="AMBIGUOUS_PRODUCT",
    )
    assert to_resolved_query(result) is None


# =============================================
# QB-05 — PRODUCT_NOT_FOUND
# =============================================

def test_qb05_product_not_found_does_not_cross_boundary():
    result = QueryResolutionResult(
        status=QueryResolutionStatus.PRODUCT_NOT_FOUND,
        query_type=QueryType.QUERY_PRICE,
        reason_code="PRODUCT_NOT_FOUND",
    )
    assert to_resolved_query(result) is None


# =============================================
# QB-06 — evidence non-propagation
# =============================================

def test_qb06_evidence_is_not_automatically_propagated():
    result = QueryResolutionResult(
        status=QueryResolutionStatus.RESOLVED,
        query_type=QueryType.QUERY_PRICE,
        product_id="CQ-44",
        evidence=["some_resolution_evidence"],
    )
    rq = to_resolved_query(result)
    assert rq is not None
    assert rq.evidence == []


# =============================================
# QB-07 — invalid runtime query_type
# =============================================

def test_qb07_invalid_runtime_query_type_does_not_cross_boundary():
    """
    Runtime type safety: passing a raw string as query_type must NOT
    silently coerce into a QueryType. Boundary returns None.
    """
    result = QueryResolutionResult(
        status=QueryResolutionStatus.RESOLVED,
        query_type="QUERY_PRICE",
        product_id="CQ-44",
    )
    assert to_resolved_query(result) is None


def test_qb07b_invalid_runtime_query_type_variants():
    """Other invalid runtime types also rejected — no coercion at all."""
    invalid_values = [
        "QUERY_PRICE",
        "QUERY_AVAILABILITY",
        "NOT_A_QUERY_TYPE",
        None,
        42,
        object(),
    ]
    for bad in invalid_values:
        result = QueryResolutionResult(
            status=QueryResolutionStatus.RESOLVED,
            query_type=bad,
            product_id="CQ-44",
        )
        assert to_resolved_query(result) is None, (
            f"boundary accepted invalid query_type={bad!r}"
        )


# =============================================
# QB-08 — deterministic conversion
# =============================================

def test_qb08_determinism_same_input_semantically_equal_output():
    result = QueryResolutionResult(
        status=QueryResolutionStatus.RESOLVED,
        query_type=QueryType.QUERY_PRICE,
        product_id="CQ-44",
    )
    rq1 = to_resolved_query(result)
    rq2 = to_resolved_query(result)
    assert rq1 is not None and rq2 is not None
    assert rq1.query_type == rq2.query_type
    assert rq1.product_id == rq2.product_id
    assert rq1.evidence == rq2.evidence


# =============================================
# QB-09 — no input mutation
# =============================================

def test_qb09_boundary_does_not_mutate_input():
    result = QueryResolutionResult(
        status=QueryResolutionStatus.RESOLVED,
        query_type=QueryType.QUERY_PRICE,
        product_id="CQ-44",
        evidence=["x", "y"],
    )
    snapshot = (
        result.status,
        result.query_type,
        result.product_id,
        result.reason_code,
        list(result.evidence),
    )
    _ = to_resolved_query(result)
    assert (
        result.status,
        result.query_type,
        result.product_id,
        result.reason_code,
        result.evidence,
    ) == snapshot


# =============================================
# QB-10 — dependency isolation
# =============================================

def test_qb10a_boundary_does_not_import_order_engine(boundary_source):
    import_re = re.compile(
        r"^\s*(?:from\s+order\.engine\s+import|import\s+order\.engine)",
        re.MULTILINE,
    )
    assert not import_re.search(boundary_source)


def test_qb10b_boundary_does_not_import_order_state(boundary_source):
    import_re = re.compile(
        r"^\s*(?:from\s+order\.state\s+import|import\s+order\.state)",
        re.MULTILINE,
    )
    assert not import_re.search(boundary_source)


def test_qb10c_boundary_does_not_import_operation_fields(boundary_source):
    import_re = re.compile(
        r"^\s*(?:from\s+order\.operation_fields\s+import|import\s+order\.operation_fields)",
        re.MULTILINE,
    )
    assert not import_re.search(boundary_source)


def test_qb10d_boundary_does_not_import_catalog_retriever(boundary_source):
    import_re = re.compile(
        r"^\s*(?:from\s+order\.catalog_retriever\s+import|import\s+order\.catalog_retriever)",
        re.MULTILINE,
    )
    assert not import_re.search(boundary_source)


def test_qb10e_boundary_does_not_import_product_resolver(boundary_source):
    import_re = re.compile(
        r"^\s*(?:from\s+order\.product_resolver\s+import|import\s+order\.product_resolver)",
        re.MULTILINE,
    )
    assert not import_re.search(boundary_source)


# =============================================
# Post-condition — every returned has is_valid() == True
# =============================================

def test_every_returned_resolved_query_is_valid():
    cases = [
        QueryResolutionResult(
            status=QueryResolutionStatus.RESOLVED,
            query_type=QueryType.QUERY_PRICE,
            product_id="CQ-44",
        ),
        QueryResolutionResult(
            status=QueryResolutionStatus.RESOLVED,
            query_type=QueryType.QUERY_AVAILABILITY,
            product_id="CQ-28",
        ),
    ]
    for r in cases:
        rq = to_resolved_query(r)
        assert rq is not None
        assert rq.is_valid() is True