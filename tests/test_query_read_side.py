import ast
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from order.fact_retrieval_result import (
    FactRetrievalResult,
    FactRetrievalStatus,
)
from order.query_resolution_result import (
    QueryResolutionResult,
    QueryResolutionStatus,
)
from order.resolution_result import OutcomeType, ResolutionResult
from order.resolved_query import QueryType, ResolvedQuery

from pipeline.application_caller import CallerResult
from pipeline.query_read_side import (
    QueryReadSideResult,
    QueryReadSideStatus,
    compose_query_read_side,
)


_MODULE_PATH = (
    Path(__file__).parent.parent / "pipeline" / "query_read_side.py"
)


def _qr(status, product_id=None):
    return QueryResolutionResult(
        status=status,
        query_type=QueryType.QUERY_PRICE,
        product_id=product_id,
        reason_code=None,
        evidence=[],
    )


def _resolved_query():
    return ResolvedQuery(
        query_type=QueryType.QUERY_PRICE, product_id="SKU-1"
    )


def _fact_retrieval(rq):
    return FactRetrievalResult(
        query=rq, status=FactRetrievalStatus.SOURCE_UNAVAILABLE
    )


def _command_result():
    return ResolutionResult(outcome=OutcomeType.NO_OP)


class _BoundarySpy:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def __call__(self, qr):
        self.calls.append(qr)
        return self.result


class _RetrieveSpy:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def __call__(self, rq):
        self.calls.append(rq)
        return self.result


# =============================================
# QRS-01 — NOT_INVOKED
# =============================================

def test_qrs01_query_none_yields_not_invoked():
    spy_b = _BoundarySpy(None)
    spy_r = _RetrieveSpy(None)
    result = compose_query_read_side(
        CallerResult(query=None, command=None),
        to_resolved_query_fn=spy_b,
        retrieve_fact_fn=spy_r,
    )
    assert result.status is QueryReadSideStatus.NOT_INVOKED
    assert result.query_resolution is None
    assert result.resolved_query is None
    assert result.fact_retrieval is None
    assert spy_b.calls == []
    assert spy_r.calls == []


def test_qrs01b_command_preserved_untouched():
    cmd = _command_result()
    spy_b = _BoundarySpy(None)
    spy_r = _RetrieveSpy(None)
    caller_result = CallerResult(query=None, command=cmd)
    compose_query_read_side(
        caller_result,
        to_resolved_query_fn=spy_b,
        retrieve_fact_fn=spy_r,
    )
    assert caller_result.command is cmd


# =============================================
# QRS-02 — NOT_RESOLVED
# =============================================

@pytest.mark.parametrize(
    "status",
    [
        QueryResolutionStatus.NEEDS_CLARIFICATION,
        QueryResolutionStatus.PRODUCT_NOT_FOUND,
    ],
)
def test_qrs02_not_resolved_statuses(status):
    qr = _qr(status)
    spy_b = _BoundarySpy(None)
    spy_r = _RetrieveSpy(None)
    result = compose_query_read_side(
        CallerResult(query=qr, command=None),
        to_resolved_query_fn=spy_b,
        retrieve_fact_fn=spy_r,
    )
    assert result.status is QueryReadSideStatus.NOT_RESOLVED
    assert result.query_resolution is qr
    assert result.resolved_query is None
    assert result.fact_retrieval is None
    assert spy_b.calls == [qr]
    assert spy_r.calls == []


def test_qrs02b_not_resolved_never_yields_source_unavailable():
    qr = _qr(QueryResolutionStatus.NEEDS_CLARIFICATION)
    result = compose_query_read_side(
        CallerResult(query=qr, command=None),
        to_resolved_query_fn=_BoundarySpy(None),
        retrieve_fact_fn=_RetrieveSpy(None),
    )
    assert result.fact_retrieval is None


# =============================================
# QRS-03 — RETRIEVED
# =============================================

def test_qrs03_resolved_yields_retrieved():
    qr = _qr(QueryResolutionStatus.RESOLVED, product_id="SKU-1")
    rq = _resolved_query()
    fr = _fact_retrieval(rq)
    spy_b = _BoundarySpy(rq)
    spy_r = _RetrieveSpy(fr)
    result = compose_query_read_side(
        CallerResult(query=qr, command=None),
        to_resolved_query_fn=spy_b,
        retrieve_fact_fn=spy_r,
    )
    assert result.status is QueryReadSideStatus.RETRIEVED
    assert result.query_resolution is qr
    assert result.resolved_query is rq
    assert result.fact_retrieval is fr


def test_qrs03b_each_step_called_exactly_once():
    qr = _qr(QueryResolutionStatus.RESOLVED, product_id="SKU-1")
    rq = _resolved_query()
    fr = _fact_retrieval(rq)
    spy_b = _BoundarySpy(rq)
    spy_r = _RetrieveSpy(fr)
    compose_query_read_side(
        CallerResult(query=qr, command=None),
        to_resolved_query_fn=spy_b,
        retrieve_fact_fn=spy_r,
    )
    assert len(spy_b.calls) == 1
    assert len(spy_r.calls) == 1


def test_qrs03c_retrieve_receives_boundary_output():
    qr = _qr(QueryResolutionStatus.RESOLVED, product_id="SKU-1")
    rq = _resolved_query()
    fr = _fact_retrieval(rq)
    spy_b = _BoundarySpy(rq)
    spy_r = _RetrieveSpy(fr)
    compose_query_read_side(
        CallerResult(query=qr, command=None),
        to_resolved_query_fn=spy_b,
        retrieve_fact_fn=spy_r,
    )
    assert spy_r.calls[0] is rq


def test_qrs03d_source_unavailable_preserved():
    qr = _qr(QueryResolutionStatus.RESOLVED, product_id="SKU-1")
    rq = _resolved_query()
    fr = _fact_retrieval(rq)
    result = compose_query_read_side(
        CallerResult(query=qr, command=None),
        to_resolved_query_fn=_BoundarySpy(rq),
        retrieve_fact_fn=_RetrieveSpy(fr),
    )
    assert (
        result.fact_retrieval.status
        is FactRetrievalStatus.SOURCE_UNAVAILABLE
    )


# =============================================
# QRS-04 — command never processed
# =============================================

def test_qrs04_command_only_does_not_invoke_read_side():
    spy_b = _BoundarySpy(None)
    spy_r = _RetrieveSpy(None)
    result = compose_query_read_side(
        CallerResult(query=None, command=_command_result()),
        to_resolved_query_fn=spy_b,
        retrieve_fact_fn=spy_r,
    )
    assert result.status is QueryReadSideStatus.NOT_INVOKED
    assert spy_b.calls == []
    assert spy_r.calls == []


def test_qrs04b_both_present_query_processed_command_untouched():
    qr = _qr(QueryResolutionStatus.RESOLVED, product_id="SKU-1")
    rq = _resolved_query()
    fr = _fact_retrieval(rq)
    cmd = _command_result()
    caller_result = CallerResult(query=qr, command=cmd)
    result = compose_query_read_side(
        caller_result,
        to_resolved_query_fn=_BoundarySpy(rq),
        retrieve_fact_fn=_RetrieveSpy(fr),
    )
    assert result.status is QueryReadSideStatus.RETRIEVED
    assert caller_result.command is cmd


# =============================================
# QRS-05 — result frozen
# =============================================

def test_qrs05_result_is_frozen():
    r = QueryReadSideResult(status=QueryReadSideStatus.NOT_INVOKED)
    with pytest.raises(FrozenInstanceError):
        r.status = QueryReadSideStatus.RETRIEVED


def test_qrs05b_result_has_only_expected_fields():
    fields = set(QueryReadSideResult.__dataclass_fields__.keys())
    assert fields == {
        "status",
        "query_resolution",
        "resolved_query",
        "fact_retrieval",
    }


def test_qrs05c_no_payload_or_rendering_fields():
    fields = set(QueryReadSideResult.__dataclass_fields__.keys())
    for forbidden in (
        "payload", "response", "message", "text",
        "price", "currency", "quantity_on_hand",
    ):
        assert forbidden not in fields


# =============================================
# QRS-06 — dependency isolation
# =============================================

_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "enum",
    "typing",
    "order.fact_read_side",
    "order.fact_retrieval_result",
    "order.query_boundary",
    "order.query_resolution_result",
    "order.resolved_query",
    "pipeline.application_caller",
}


def test_qrs06_imports_only_expected():
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module in _ALLOWED_IMPORTS, (
                f"unexpected import: {node.module}"
            )
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name in _ALLOWED_IMPORTS, (
                    f"unexpected import: {alias.name}"
                )


def test_qrs06b_no_forbidden_symbols_in_code():
    source = _MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

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

    forbidden = (
        "OrderState",
        "OrderEngine",
        "execute_resolution",
        "resolve_query",
        "resolve_operation",
        "catalog_retriever",
        "product_resolver",
        "CommandRecognizer",
        "SignalObservation",
        "DispatchPlan",
        "ModularAdapter",
    )
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstring_ids
        ):
            for token in forbidden:
                assert token not in node.value, (
                    f"non-docstring string references {token!r}"
                )


# =============================================
# QRS-07 — determinism
# =============================================

def test_qrs07_determinism():
    qr = _qr(QueryResolutionStatus.RESOLVED, product_id="SKU-1")
    rq = _resolved_query()
    fr = _fact_retrieval(rq)
    caller_result = CallerResult(query=qr, command=None)

    def run():
        return compose_query_read_side(
            caller_result,
            to_resolved_query_fn=_BoundarySpy(rq),
            retrieve_fact_fn=_RetrieveSpy(fr),
        )

    results = [run() for _ in range(5)]
    assert all(r.status is results[0].status for r in results)
    assert all(r.fact_retrieval is fr for r in results)