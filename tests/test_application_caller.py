import ast
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from order.query_resolution_result import (
    QueryResolutionResult,
    QueryResolutionStatus,
)
from order.resolution_result import OutcomeType, ResolutionResult
from order.resolved_query import QueryType
from order.state import OrderState

from pipeline.application_caller import (
    CallerResult,
    DomainInvocationInconsistency,
    invoke,
)
from pipeline.dispatch_plan import (
    DispatchAction,
    DispatchDecision,
    DispatchPlan,
    DispatchTarget,
)
from pipeline.query_intent_provider import QueryIntentSignal
from pipeline.semantic_intent_router import SemanticIntent
from pipeline.signal_observation import (
    CommandEvidence,
    CommandObservation,
    QueryObservation,
    SignalObservation,
)


_MODULE_PATH = (
    Path(__file__).parent.parent / "pipeline" / "application_caller.py"
)


# =============================================
# helpers
# =============================================

def _plan(query_action, command_action):
    return DispatchPlan(decisions=(
        DispatchDecision(DispatchTarget.QUERY, query_action),
        DispatchDecision(DispatchTarget.COMMAND, command_action),
    ))


def _obs(query_signal=None, command_evidence=None):
    q = None if query_signal is None else QueryObservation(signal=query_signal)
    c = (
        None
        if command_evidence is None
        else CommandObservation(evidence=command_evidence)
    )
    return SignalObservation(query=q, command=c)


def _query_result():
    return QueryResolutionResult(
        status=QueryResolutionStatus.PRODUCT_NOT_FOUND,
        query_type=QueryType.QUERY_PRICE,
        product_id=None,
        reason_code="TEST",
        evidence=[],
    )


def _command_result():
    return ResolutionResult(outcome=OutcomeType.NO_OP)


class _QuerySpy:
    def __init__(self, result=None):
        self.result = result if result is not None else _query_result()
        self.calls = []

    def __call__(self, message, semantic_intent):
        self.calls.append((message, semantic_intent))
        return self.result


class _CommandSpy:
    def __init__(self, result=None):
        self.result = result if result is not None else _command_result()
        self.calls = []

    def __call__(self, message, state):
        self.calls.append((message, state))
        return self.result


# =============================================
# CALL-01 — no dispatch
# =============================================

def test_call01_no_dispatch_returns_empty_result():
    spy_q = _QuerySpy()
    spy_c = _CommandSpy()
    result = invoke(
        "x",
        SignalObservation(),
        _plan(DispatchAction.NO_DISPATCH_NO_OBSERVATION,
              DispatchAction.NO_DISPATCH_NO_OBSERVATION),
        OrderState(),
        resolve_query_fn=spy_q,
        resolve_operation_fn=spy_c,
    )
    assert isinstance(result, CallerResult)
    assert result.query is None
    assert result.command is None
    assert spy_q.calls == []
    assert spy_c.calls == []


# =============================================
# CALL-02 — query only
# =============================================

def test_call02_query_only():
    spy_q = _QuerySpy()
    spy_c = _CommandSpy()
    obs = _obs(query_signal=QueryIntentSignal.QUERY_PRICE)
    result = invoke(
        "quanto custa brie?",
        obs,
        _plan(DispatchAction.DISPATCH, DispatchAction.NO_DISPATCH_NO_OBSERVATION),
        OrderState(),
        resolve_query_fn=spy_q,
        resolve_operation_fn=spy_c,
    )
    assert result.query is spy_q.result
    assert result.command is None
    assert len(spy_q.calls) == 1
    assert spy_c.calls == []


def test_call02b_query_availability_uses_availability_semantic_intent():
    spy_q = _QuerySpy()
    spy_c = _CommandSpy()
    obs = _obs(query_signal=QueryIntentSignal.QUERY_AVAILABILITY)
    invoke(
        "tem brie?",
        obs,
        _plan(DispatchAction.DISPATCH, DispatchAction.NO_DISPATCH_NO_OBSERVATION),
        OrderState(),
        resolve_query_fn=spy_q,
        resolve_operation_fn=spy_c,
    )
    assert len(spy_q.calls) == 1
    message, semantic_intent = spy_q.calls[0]
    assert message == "tem brie?"
    assert semantic_intent is SemanticIntent.QUERY_AVAILABILITY


def test_call02c_query_uses_preserved_signal():
    """Caller translates from observation.query.signal, not re-observation."""
    spy_q = _QuerySpy()
    obs = _obs(query_signal=QueryIntentSignal.QUERY_PRICE)
    invoke(
        "message",
        obs,
        _plan(DispatchAction.DISPATCH, DispatchAction.NO_DISPATCH_NO_OBSERVATION),
        OrderState(),
        resolve_query_fn=spy_q,
        resolve_operation_fn=_CommandSpy(),
    )
    assert spy_q.calls[0][1] is SemanticIntent.QUERY_PRICE


# =============================================
# CALL-03 — command only
# =============================================

def test_call03_command_only():
    spy_q = _QuerySpy()
    spy_c = _CommandSpy()
    obs = _obs(command_evidence=CommandEvidence.PRESENT)
    state = OrderState()
    result = invoke(
        "manda dois brie",
        obs,
        _plan(DispatchAction.NO_DISPATCH_NO_OBSERVATION, DispatchAction.DISPATCH),
        state,
        resolve_query_fn=spy_q,
        resolve_operation_fn=spy_c,
    )
    assert result.query is None
    assert result.command is spy_c.result
    assert spy_q.calls == []
    assert len(spy_c.calls) == 1
    assert spy_c.calls[0][0] == "manda dois brie"
    assert spy_c.calls[0][1] is state


# =============================================
# CALL-04 — both dispatch
# =============================================

def test_call04_both_dispatch():
    spy_q = _QuerySpy()
    spy_c = _CommandSpy()
    obs = _obs(
        query_signal=QueryIntentSignal.QUERY_PRICE,
        command_evidence=CommandEvidence.PRESENT,
    )
    result = invoke(
        "x",
        obs,
        _plan(DispatchAction.DISPATCH, DispatchAction.DISPATCH),
        OrderState(),
        resolve_query_fn=spy_q,
        resolve_operation_fn=spy_c,
    )
    assert result.query is spy_q.result
    assert result.command is spy_c.result
    assert len(spy_q.calls) == 1
    assert len(spy_c.calls) == 1


def test_call04b_each_domain_called_exactly_once():
    spy_q = _QuerySpy()
    spy_c = _CommandSpy()
    obs = _obs(
        query_signal=QueryIntentSignal.QUERY_AVAILABILITY,
        command_evidence=CommandEvidence.PRESENT,
    )
    invoke(
        "x", obs,
        _plan(DispatchAction.DISPATCH, DispatchAction.DISPATCH),
        OrderState(),
        resolve_query_fn=spy_q,
        resolve_operation_fn=spy_c,
    )
    assert len(spy_q.calls) == 1
    assert len(spy_c.calls) == 1


# =============================================
# CALL-05 — non-dispatched domain never called
# =============================================

@pytest.mark.parametrize(
    "query_action",
    [
        DispatchAction.NO_DISPATCH_UNRESOLVED,
        DispatchAction.NO_DISPATCH_NOT_QUERY,
        DispatchAction.NO_DISPATCH_NO_OBSERVATION,
    ],
)
def test_call05_query_not_dispatched_never_called(query_action):
    spy_q = _QuerySpy()
    spy_c = _CommandSpy()
    obs = _obs(
        query_signal=QueryIntentSignal.UNRESOLVED,
        command_evidence=CommandEvidence.PRESENT,
    )
    invoke(
        "x", obs,
        _plan(query_action, DispatchAction.DISPATCH),
        OrderState(),
        resolve_query_fn=spy_q,
        resolve_operation_fn=spy_c,
    )
    assert spy_q.calls == []
    assert len(spy_c.calls) == 1


@pytest.mark.parametrize(
    "command_action",
    [
        DispatchAction.NO_DISPATCH_INDETERMINATE,
        DispatchAction.NO_DISPATCH_ABSENT,
        DispatchAction.NO_DISPATCH_NO_OBSERVATION,
    ],
)
def test_call05b_command_not_dispatched_never_called(command_action):
    spy_q = _QuerySpy()
    spy_c = _CommandSpy()
    obs = _obs(
        query_signal=QueryIntentSignal.QUERY_PRICE,
        command_evidence=CommandEvidence.INDETERMINATE,
    )
    invoke(
        "x", obs,
        _plan(DispatchAction.DISPATCH, command_action),
        OrderState(),
        resolve_query_fn=spy_q,
        resolve_operation_fn=spy_c,
    )
    assert len(spy_q.calls) == 1
    assert spy_c.calls == []


# =============================================
# CALL-06 — incoherence (T10-P47)
# =============================================

def test_call06_query_dispatch_missing_observation():
    with pytest.raises(DomainInvocationInconsistency) as e:
        invoke(
            "x",
            SignalObservation(),
            _plan(DispatchAction.DISPATCH, DispatchAction.NO_DISPATCH_NO_OBSERVATION),
            OrderState(),
            resolve_query_fn=_QuerySpy(),
            resolve_operation_fn=_CommandSpy(),
        )
    assert e.value.target is DispatchTarget.QUERY


@pytest.mark.parametrize(
    "signal",
    [QueryIntentSignal.UNRESOLVED, QueryIntentSignal.NOT_QUERY],
)
def test_call06b_query_dispatch_non_dispatchable_signal(signal):
    with pytest.raises(DomainInvocationInconsistency):
        invoke(
            "x",
            _obs(query_signal=signal),
            _plan(DispatchAction.DISPATCH, DispatchAction.NO_DISPATCH_NO_OBSERVATION),
            OrderState(),
            resolve_query_fn=_QuerySpy(),
            resolve_operation_fn=_CommandSpy(),
        )


def test_call06c_command_dispatch_missing_observation():
    with pytest.raises(DomainInvocationInconsistency) as e:
        invoke(
            "x",
            SignalObservation(),
            _plan(DispatchAction.NO_DISPATCH_NO_OBSERVATION, DispatchAction.DISPATCH),
            OrderState(),
            resolve_query_fn=_QuerySpy(),
            resolve_operation_fn=_CommandSpy(),
        )
    assert e.value.target is DispatchTarget.COMMAND


@pytest.mark.parametrize(
    "evidence",
    [CommandEvidence.INDETERMINATE, CommandEvidence.ABSENT],
)
def test_call06d_command_dispatch_non_present_evidence(evidence):
    with pytest.raises(DomainInvocationInconsistency):
        invoke(
            "x",
            _obs(command_evidence=evidence),
            _plan(DispatchAction.NO_DISPATCH_NO_OBSERVATION, DispatchAction.DISPATCH),
            OrderState(),
            resolve_query_fn=_QuerySpy(),
            resolve_operation_fn=_CommandSpy(),
        )


def test_call06e_incoherence_fails_before_any_pipeline_call():
    spy_q = _QuerySpy()
    spy_c = _CommandSpy()
    with pytest.raises(DomainInvocationInconsistency):
        invoke(
            "x",
            _obs(
                query_signal=QueryIntentSignal.QUERY_PRICE,
                command_evidence=CommandEvidence.INDETERMINATE,
            ),
            _plan(DispatchAction.DISPATCH, DispatchAction.DISPATCH),
            OrderState(),
            resolve_query_fn=spy_q,
            resolve_operation_fn=spy_c,
        )
    assert spy_q.calls == []
    assert spy_c.calls == []


# =============================================
# CALL-07 — CallerResult structure
# =============================================

def test_call07_caller_result_frozen():
    r = CallerResult(query=None, command=None)
    with pytest.raises(FrozenInstanceError):
        r.query = "nope"


def test_call07b_caller_result_has_only_expected_fields():
    fields = set(CallerResult.__dataclass_fields__.keys())
    assert fields == {"query", "command"}


def test_call07c_no_invoked_priority_or_payload_fields():
    fields = set(CallerResult.__dataclass_fields__.keys())
    for forbidden in ("invoked", "priority", "payload", "status", "ok"):
        assert forbidden not in fields


# =============================================
# CALL-08 — determinism
# =============================================

def test_call08_determinism():
    spy_q = _QuerySpy()
    spy_c = _CommandSpy()
    obs = _obs(
        query_signal=QueryIntentSignal.QUERY_PRICE,
        command_evidence=CommandEvidence.PRESENT,
    )
    plan = _plan(DispatchAction.DISPATCH, DispatchAction.DISPATCH)
    state = OrderState()
    results = [
        invoke("x", obs, plan, state,
               resolve_query_fn=spy_q, resolve_operation_fn=spy_c)
        for _ in range(5)
    ]
    assert all(r.query is results[0].query for r in results)
    assert all(r.command is results[0].command for r in results)


# =============================================
# CALL-09 — no execution / boundary involvement
# =============================================

_FORBIDDEN_MODULES = frozenset({
    "order.engine",
    "order.execution",
    "order.resolution_boundary",
    "benchmark.adapters.modular",
})

_FORBIDDEN_SYMBOLS = (
    "to_resolved_query",
    "to_resolved_operation",
    "execute_resolution",
    "OrderEngine",
    "CommandRecognizer",
    "ModularAdapter",
    "CommandLabel",
)


def test_call09_no_execution_modules_imported():
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module not in _FORBIDDEN_MODULES, (
                f"forbidden import: {node.module}"
            )
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name not in _FORBIDDEN_MODULES, (
                    f"forbidden import: {alias.name}"
                )


def test_call09b_no_forbidden_symbols_in_code():
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

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstring_ids
        ):
            for token in _FORBIDDEN_SYMBOLS:
                assert token not in node.value, (
                    f"non-docstring string references {token!r}"
                )


def test_call09c_command_label_not_imported():
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                assert alias.name != "CommandLabel"
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "CommandLabel"


# =============================================
# CALL-10 — imports whitelist
# =============================================

def test_call10_imports_only_expected_modules():
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    allowed = {
        "__future__",
        "dataclasses",
        "typing",
        "order.state",
        "order.resolution_result",
        "order.query_resolution_result",
        "pipeline.dispatch_plan",
        "pipeline.query_intent_provider",
        "pipeline.query_resolution_pipeline",
        "pipeline.query_signal_translation",
        "pipeline.resolution_pipeline",
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