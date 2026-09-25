import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from pipeline.query_intent_provider import QueryIntentSignal
from pipeline.query_signal_translation import (
    NonDispatchableQuerySignal,
    query_signal_to_semantic_intent,
)
from pipeline.semantic_intent_router import SemanticIntent


_MODULE_PATH = (
    Path(__file__).parent.parent
    / "pipeline"
    / "query_signal_translation.py"
)


# =============================================
# QST-01 — valid translations
# =============================================

def test_qst01_query_price():
    result = query_signal_to_semantic_intent(
        QueryIntentSignal.QUERY_PRICE
    )
    assert result is SemanticIntent.QUERY_PRICE


def test_qst01b_query_availability():
    result = query_signal_to_semantic_intent(
        QueryIntentSignal.QUERY_AVAILABILITY
    )
    assert result is SemanticIntent.QUERY_AVAILABILITY


# =============================================
# QST-02 — explicit failure for non-dispatchable
# =============================================

def test_qst02_unresolved_raises():
    with pytest.raises(NonDispatchableQuerySignal) as excinfo:
        query_signal_to_semantic_intent(QueryIntentSignal.UNRESOLVED)
    assert excinfo.value.signal is QueryIntentSignal.UNRESOLVED


def test_qst02b_not_query_raises():
    with pytest.raises(NonDispatchableQuerySignal) as excinfo:
        query_signal_to_semantic_intent(QueryIntentSignal.NOT_QUERY)
    assert excinfo.value.signal is QueryIntentSignal.NOT_QUERY


def test_qst02c_no_none_return_for_invalid_inputs():
    for signal in (
        QueryIntentSignal.UNRESOLVED,
        QueryIntentSignal.NOT_QUERY,
    ):
        try:
            result = query_signal_to_semantic_intent(signal)
        except NonDispatchableQuerySignal:
            continue
        pytest.fail(
            f"expected NonDispatchableQuerySignal for {signal}, "
            f"got {result!r}"
        )


# =============================================
# QST-03 — determinism
# =============================================

def test_qst03_determinism():
    for signal in (
        QueryIntentSignal.QUERY_PRICE,
        QueryIntentSignal.QUERY_AVAILABILITY,
    ):
        results = [
            query_signal_to_semantic_intent(signal) for _ in range(5)
        ]
        assert all(r is results[0] for r in results)


# =============================================
# QST-04 — dependency isolation
# =============================================

def test_qst04_imports_only_allowed_modules():
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    allowed = {
        "__future__",
        "pipeline.query_intent_provider",
        "pipeline.semantic_intent_router",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module in allowed, (
                f"unexpected import: {node.module}"
            )
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name in allowed, (
                    f"unexpected import: {alias.name}"
                )


def test_qst04b_no_forbidden_symbols_in_code():
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
        "DispatchPlan",
        "SignalObservation",
        "OrderState",
        "OrderEngine",
        "resolve_query",
        "resolve_operation",
        "CommandEvidence",
        "CommandRecognizer",
        "catalog_retriever",
        "product_resolver",
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
                    f"non-docstring string references {token!r}: "
                    f"{node.value!r}"
                )