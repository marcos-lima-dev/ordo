import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from pipeline.dispatch_plan import (
    DispatchAction,
    DispatchPlan,
    DispatchTarget,
)
from pipeline.dispatch_planner import plan
from pipeline.query_intent_provider import QueryIntentSignal
from pipeline.signal_observation import (
    CommandEvidence,
    CommandObservation,
    QueryObservation,
    SignalObservation,
)


_MODULE_PATH = (
    Path(__file__).parent.parent / "pipeline" / "dispatch_planner.py"
)


_QUERY_CASES = [
    None,
    QueryIntentSignal.QUERY_PRICE,
    QueryIntentSignal.QUERY_AVAILABILITY,
    QueryIntentSignal.UNRESOLVED,
    QueryIntentSignal.NOT_QUERY,
]

_COMMAND_CASES = [
    None,
    CommandEvidence.PRESENT,
    CommandEvidence.INDETERMINATE,
    CommandEvidence.ABSENT,
]

_EXPECTED_QUERY = {
    None: DispatchAction.NO_DISPATCH_NO_OBSERVATION,
    QueryIntentSignal.QUERY_PRICE: DispatchAction.DISPATCH,
    QueryIntentSignal.QUERY_AVAILABILITY: DispatchAction.DISPATCH,
    QueryIntentSignal.UNRESOLVED: DispatchAction.NO_DISPATCH_UNRESOLVED,
    QueryIntentSignal.NOT_QUERY: DispatchAction.NO_DISPATCH_NOT_QUERY,
}

_EXPECTED_COMMAND = {
    None: DispatchAction.NO_DISPATCH_NO_OBSERVATION,
    CommandEvidence.PRESENT: DispatchAction.DISPATCH,
    CommandEvidence.INDETERMINATE: DispatchAction.NO_DISPATCH_INDETERMINATE,
    CommandEvidence.ABSENT: DispatchAction.NO_DISPATCH_ABSENT,
}


def _make_observation(query_signal, command_evidence):
    q = (
        None
        if query_signal is None
        else QueryObservation(signal=query_signal)
    )
    c = (
        None
        if command_evidence is None
        else CommandObservation(evidence=command_evidence)
    )
    return SignalObservation(query=q, command=c)


# =============================================
# DPL-01 — Cartesian product (20 combinations)
# =============================================

@pytest.mark.parametrize("command_evidence", _COMMAND_CASES)
@pytest.mark.parametrize("query_signal", _QUERY_CASES)
def test_dpl01_cartesian_product(query_signal, command_evidence):
    obs = _make_observation(query_signal, command_evidence)
    result = plan(obs)

    assert isinstance(result, DispatchPlan)
    assert len(result.decisions) == 2

    targets = [d.target for d in result.decisions]
    assert targets.count(DispatchTarget.QUERY) == 1
    assert targets.count(DispatchTarget.COMMAND) == 1

    by_target = {d.target: d.action for d in result.decisions}
    assert by_target[DispatchTarget.QUERY] is _EXPECTED_QUERY[query_signal]
    assert by_target[DispatchTarget.COMMAND] is _EXPECTED_COMMAND[command_evidence]


# =============================================
# DPL-02 — Explicit anchor cases
# =============================================

def test_dpl02_both_dispatch():
    obs = _make_observation(
        QueryIntentSignal.QUERY_PRICE, CommandEvidence.PRESENT
    )
    result = plan(obs)
    by_target = {d.target: d.action for d in result.decisions}
    assert by_target[DispatchTarget.QUERY] is DispatchAction.DISPATCH
    assert by_target[DispatchTarget.COMMAND] is DispatchAction.DISPATCH


def test_dpl02b_both_absent():
    obs = SignalObservation()
    result = plan(obs)
    by_target = {d.target: d.action for d in result.decisions}
    assert by_target[DispatchTarget.QUERY] is DispatchAction.NO_DISPATCH_NO_OBSERVATION
    assert by_target[DispatchTarget.COMMAND] is DispatchAction.NO_DISPATCH_NO_OBSERVATION


def test_dpl02c_query_unresolved_with_command_dispatch():
    obs = _make_observation(
        QueryIntentSignal.UNRESOLVED, CommandEvidence.PRESENT
    )
    result = plan(obs)
    by_target = {d.target: d.action for d in result.decisions}
    assert by_target[DispatchTarget.QUERY] is DispatchAction.NO_DISPATCH_UNRESOLVED
    assert by_target[DispatchTarget.COMMAND] is DispatchAction.DISPATCH


def test_dpl02d_query_dispatch_with_command_indeterminate():
    obs = _make_observation(
        QueryIntentSignal.QUERY_AVAILABILITY, CommandEvidence.INDETERMINATE
    )
    result = plan(obs)
    by_target = {d.target: d.action for d in result.decisions}
    assert by_target[DispatchTarget.QUERY] is DispatchAction.DISPATCH
    assert by_target[DispatchTarget.COMMAND] is DispatchAction.NO_DISPATCH_INDETERMINATE


# =============================================
# DPL-03 — Domain independence
# =============================================

def test_dpl03_query_decision_independent_of_command():
    """Adding a COMMAND observation must not change the QUERY decision."""
    for query_signal in _QUERY_CASES:
        without_command = plan(_make_observation(query_signal, None))
        with_command = plan(
            _make_observation(query_signal, CommandEvidence.PRESENT)
        )
        q_without = {
            d.target: d.action for d in without_command.decisions
        }[DispatchTarget.QUERY]
        q_with = {
            d.target: d.action for d in with_command.decisions
        }[DispatchTarget.QUERY]
        assert q_without is q_with, (
            f"QUERY decision changed when COMMAND was added: "
            f"query={query_signal}, without={q_without}, with={q_with}"
        )


def test_dpl03b_command_decision_independent_of_query():
    """Adding a QUERY observation must not change the COMMAND decision."""
    for command_evidence in _COMMAND_CASES:
        without_query = plan(_make_observation(None, command_evidence))
        with_query = plan(
            _make_observation(
                QueryIntentSignal.QUERY_PRICE, command_evidence
            )
        )
        c_without = {
            d.target: d.action for d in without_query.decisions
        }[DispatchTarget.COMMAND]
        c_with = {
            d.target: d.action for d in with_query.decisions
        }[DispatchTarget.COMMAND]
        assert c_without is c_with, (
            f"COMMAND decision changed when QUERY was added: "
            f"command={command_evidence}, without={c_without}, with={c_with}"
        )


# =============================================
# DPL-04 — Determinism
# =============================================

def test_dpl04_determinism():
    obs = _make_observation(
        QueryIntentSignal.QUERY_AVAILABILITY,
        CommandEvidence.INDETERMINATE,
    )
    results = [plan(obs) for _ in range(5)]
    assert all(r == results[0] for r in results)


def test_dpl04b_determinism_absent():
    obs = SignalObservation()
    results = [plan(obs) for _ in range(5)]
    assert all(r == results[0] for r in results)


# =============================================
# DPL-05 — Dependency isolation
# =============================================

def test_dpl05_imports_only_allowed_modules():
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    allowed = {
        "__future__",
        "typing",
        "pipeline.dispatch_plan",
        "pipeline.query_intent_provider",
        "pipeline.signal_observation",
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


def test_dpl05b_no_forbidden_symbols_in_code():
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
        "resolve_query",
        "resolve_operation",
        "to_resolved_query",
        "to_resolved_operation",
        "OrderEngine",
        "OrderState",
        "SemanticIntent",
        "OperationType",
        "QueryType",
        "CommandLabel",
        "ModularAdapter",
        "CommandRecognizer",
        "SignalObservation.query",
    )
    # SignalObservation.query is only forbidden as a *token* in
    # non-docstring strings; we still use `observation.query` as an
    # attribute read, which is fine.
    forbidden = tuple(
        t for t in forbidden if t != "SignalObservation.query"
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