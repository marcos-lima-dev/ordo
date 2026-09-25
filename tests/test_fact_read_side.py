import ast
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from order.fact_read_side import (
    InvalidResolvedQueryType,
    retrieve_fact,
)
from order.fact_retrieval_result import (
    FactRetrievalResult,
    FactRetrievalStatus,
)
from order.resolved_query import QueryType, ResolvedQuery


_FACT_READ_PATH = (
    Path(__file__).parent.parent / "order" / "fact_read_side.py"
)
_FACT_RESULT_PATH = (
    Path(__file__).parent.parent / "order" / "fact_retrieval_result.py"
)


def _rq(query_type, product_id="SKU-1"):
    return ResolvedQuery(query_type=query_type, product_id=product_id)


def _non_docstring_strings(tree):
    docstring_ids = set()
    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                docstring_ids.add(id(node.body[0].value))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstring_ids
    ]


# =============================================
# FRS-01 — state today is SOURCE_UNAVAILABLE
# =============================================

def test_frs01_price_yields_source_unavailable():
    result = retrieve_fact(_rq(QueryType.QUERY_PRICE))
    assert isinstance(result, FactRetrievalResult)
    assert result.status is FactRetrievalStatus.SOURCE_UNAVAILABLE


def test_frs01b_availability_yields_source_unavailable():
    result = retrieve_fact(_rq(QueryType.QUERY_AVAILABILITY))
    assert result.status is FactRetrievalStatus.SOURCE_UNAVAILABLE


def test_frs01c_product_id_preserved():
    rq = _rq(QueryType.QUERY_PRICE, product_id="PROV-42")
    result = retrieve_fact(rq)
    assert result.query is rq
    assert result.query.product_id == "PROV-42"


# =============================================
# FRS-02 — states are distinct
# =============================================

def test_frs02_source_unavailable_is_not_fact_not_found():
    assert (
        FactRetrievalStatus.SOURCE_UNAVAILABLE
        is not FactRetrievalStatus.FACT_NOT_FOUND
    )


def test_frs02b_source_unavailable_is_not_product_not_found():
    from order.query_resolution_result import QueryResolutionStatus
    assert (
        FactRetrievalStatus.SOURCE_UNAVAILABLE.value
        != QueryResolutionStatus.PRODUCT_NOT_FOUND.value
    )


def test_frs02c_no_found_or_not_found_produced_today():
    for qt in (QueryType.QUERY_PRICE, QueryType.QUERY_AVAILABILITY):
        result = retrieve_fact(_rq(qt))
        assert result.status not in (
            FactRetrievalStatus.FACT_FOUND,
            FactRetrievalStatus.FACT_NOT_FOUND,
        )


# =============================================
# FRS-03 — contract violation on bad query_type
# =============================================

def test_frs03_invalid_query_type_raises():
    rq = ResolvedQuery.__new__(ResolvedQuery)
    object.__setattr__(rq, "query_type", "QUERY_PRICE")
    object.__setattr__(rq, "product_id", "X")
    object.__setattr__(rq, "evidence", [])
    with pytest.raises(InvalidResolvedQueryType):
        retrieve_fact(rq)


# =============================================
# FRS-04 — result is frozen and minimal
# =============================================

def test_frs04_result_frozen():
    r = retrieve_fact(_rq(QueryType.QUERY_PRICE))
    with pytest.raises(FrozenInstanceError):
        r.status = FactRetrievalStatus.FACT_FOUND


def test_frs04b_result_has_only_query_and_status():
    fields = set(FactRetrievalResult.__dataclass_fields__.keys())
    assert fields == {"query", "status"}


def test_frs04c_no_business_payload_fields():
    fields = set(FactRetrievalResult.__dataclass_fields__.keys())
    for forbidden in (
        "price", "currency", "unit_price", "list_price",
        "quantity_on_hand", "stock", "freshness", "timestamp",
        "fact", "payload",
    ):
        assert forbidden not in fields


# =============================================
# FRS-05 — dependency isolation
# =============================================

_ALLOWED_READ_SIDE = {
    "__future__",
    "order.fact_retrieval_result",
    "order.resolved_query",
}
_ALLOWED_RESULT = {
    "__future__",
    "dataclasses",
    "enum",
    "order.resolved_query",
}


def test_frs05_read_side_imports_only_expected():
    tree = ast.parse(_FACT_READ_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module in _ALLOWED_READ_SIDE, (
                f"unexpected import: {node.module}"
            )
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name in _ALLOWED_READ_SIDE, (
                    f"unexpected import: {alias.name}"
                )


def test_frs05b_result_imports_only_expected():
    tree = ast.parse(_FACT_RESULT_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module in _ALLOWED_RESULT, (
                f"unexpected import: {node.module}"
            )
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name in _ALLOWED_RESULT, (
                    f"unexpected import: {alias.name}"
                )


def test_frs05c_no_catalog_or_engine_or_state_in_read_side():
    """
    Non-docstring strings must not reference forbidden symbols.
    Imports are already restricted by test_frs05.
    """
    source = _FACT_READ_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    forbidden = (
        "catalog_retriever",
        "product_resolver",
        "order.state",
        "order.engine",
        "OrderEngine",
        "OrderState",
        "execute_resolution",
        "resolve_query",
        "resolve_operation",
    )
    for value in _non_docstring_strings(tree):
        for token in forbidden:
            assert token not in value, (
                f"non-docstring string references {token!r}: {value!r}"
            )


# =============================================
# FRS-06 — determinism
# =============================================

def test_frs06_determinism():
    rq = _rq(QueryType.QUERY_PRICE, product_id="SKU-A")
    results = [retrieve_fact(rq) for _ in range(5)]
    assert all(r.status is results[0].status for r in results)
    assert all(r.query is rq for r in results)