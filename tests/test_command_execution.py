import ast
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from order.engine import OrderEngine
from order.execution import execute_resolution
from order.query_resolution_result import (
    QueryResolutionResult,
    QueryResolutionStatus,
)
from order.resolution_boundary import to_resolved_operation
from order.resolution_result import OutcomeType, ResolutionResult
from order.resolved_query import QueryType
from order.state import OrderState

from pipeline.application_caller import CallerResult, invoke
from pipeline.command_execution import (
    CommandExecutionResult,
    CommandExecutionStatus,
    compose_command_execution,
)
from pipeline.dispatch_plan import (
    DispatchAction,
    DispatchDecision,
    DispatchPlan,
    DispatchTarget,
)
from pipeline.signal_observation import (
    CommandEvidence,
    CommandObservation,
    SignalObservation,
)


_MODULE_PATH = (
    Path(__file__).parent.parent / "pipeline" / "command_execution.py"
)


# =============================================
# helpers
# =============================================

def _valid_operation_result(product_id="SKU-PROV", qty=5.0, unit="KG"):
    return ResolutionResult(
        outcome=OutcomeType.OPERATION,
        operation={
            "type": "ADD_ITEM",
            "product_id": product_id,
            "product_term": "provolone",
            "quantity_value": qty,
            "quantity_unit": unit,
            "target_item_id": None,
            "replacement_product_id": None,
        },
        evidence=[],
    )


class _BoundarySpy:
    def __init__(self, real=to_resolved_operation):
        self.real = real
        self.calls = []

    def __call__(self, result):
        self.calls.append(result)
        return self.real(result)


class _ExecuteSpy:
    def __init__(self, real=execute_resolution):
        self.real = real
        self.calls = []

    def __call__(self, state, result, engine):
        self.calls.append((state, result, engine))
        return self.real(state, result, engine)


class _FakeExecute:
    """Injected execute_resolution stub returning a fixed (state, events)."""

    def __init__(self, events):
        self.events = list(events)
        self.calls = []

    def __call__(self, state, result, engine):
        self.calls.append((state, result, engine))
        return state, list(self.events)


# =============================================
# CE-01 / CE-02 / CE-03 — enum and result shape
# =============================================

def test_ce01_status_enum_exact():
    assert {s.name for s in CommandExecutionStatus} == {
        "NOT_INVOKED",
        "NOT_EXECUTABLE",
        "EXECUTED",
    }


def test_ce01b_no_succeeded_failed_rejected():
    forbidden = {"SUCCEEDED", "FAILED", "REJECTED", "OK", "ERROR"}
    assert forbidden.isdisjoint({s.name for s in CommandExecutionStatus})


def test_ce02_result_frozen():
    r = CommandExecutionResult(status=CommandExecutionStatus.NOT_INVOKED)
    with pytest.raises(FrozenInstanceError):
        r.status = CommandExecutionStatus.EXECUTED


def test_ce03_result_has_only_expected_fields():
    fields = set(CommandExecutionResult.__dataclass_fields__.keys())
    assert fields == {"status", "resolution_result", "state", "events"}


def test_ce03b_no_executed_bool_field():
    fields = set(CommandExecutionResult.__dataclass_fields__.keys())
    for forbidden in (
        "executed", "succeeded", "failed", "ok", "is_executed",
    ):
        assert forbidden not in fields


# =============================================
# CE-04 — NOT_INVOKED
# =============================================

def test_ce04_command_none_yields_not_invoked():
    spy_b = _BoundarySpy()
    spy_e = _ExecuteSpy()
    state = OrderState()
    result = compose_command_execution(
        CallerResult(query=None, command=None),
        state,
        OrderEngine(),
        to_resolved_operation_fn=spy_b,
        execute_resolution_fn=spy_e,
    )
    assert result.status is CommandExecutionStatus.NOT_INVOKED
    assert result.resolution_result is None
    assert result.state is None
    assert result.events == ()
    assert spy_b.calls == []
    assert spy_e.calls == []
    assert state.items == []


# =============================================
# CE-05 — NOT_EXECUTABLE for non-OPERATION outcomes
# =============================================

@pytest.mark.parametrize(
    "outcome",
    [
        OutcomeType.NEEDS_CLARIFICATION,
        OutcomeType.BLOCKED,
        OutcomeType.NO_OP,
    ],
)
def test_ce05_non_operation_outcome_not_executable(outcome):
    spy_b = _BoundarySpy()
    spy_e = _ExecuteSpy()
    state = OrderState()
    cmd = ResolutionResult(outcome=outcome, reason_code="X")
    result = compose_command_execution(
        CallerResult(query=None, command=cmd),
        state,
        OrderEngine(),
        to_resolved_operation_fn=spy_b,
        execute_resolution_fn=spy_e,
    )
    assert result.status is CommandExecutionStatus.NOT_EXECUTABLE
    assert result.resolution_result is cmd
    assert result.state is None
    assert spy_b.calls == [cmd]
    assert spy_e.calls == []
    assert state.items == []


@pytest.mark.parametrize(
    "operation",
    [
        {},                          # missing type
        {"type": "BOGUS"},           # unknown type
        {"type": 123},               # wrong type
    ],
)
def test_ce05b_invalid_operation_dict_not_executable(operation):
    spy_b = _BoundarySpy()
    spy_e = _ExecuteSpy()
    state = OrderState()
    cmd = ResolutionResult(outcome=OutcomeType.OPERATION, operation=operation)
    result = compose_command_execution(
        CallerResult(query=None, command=cmd),
        state,
        OrderEngine(),
        to_resolved_operation_fn=spy_b,
        execute_resolution_fn=spy_e,
    )
    assert result.status is CommandExecutionStatus.NOT_EXECUTABLE
    assert result.state is None
    assert spy_e.calls == []
    assert state.items == []


# =============================================
# CE-06 — EXECUTED happy path
# =============================================

def test_ce06_valid_operation_executes():
    spy_b = _BoundarySpy()
    spy_e = _ExecuteSpy()
    engine = OrderEngine()
    state = OrderState()
    cmd = _valid_operation_result()
    result = compose_command_execution(
        CallerResult(query=None, command=cmd),
        state,
        engine,
        to_resolved_operation_fn=spy_b,
        execute_resolution_fn=spy_e,
    )
    assert result.status is CommandExecutionStatus.EXECUTED
    assert result.resolution_result is cmd
    assert result.state is state
    assert len(spy_b.calls) == 1
    assert len(spy_e.calls) == 1
    assert spy_e.calls[0][0] is state
    assert spy_e.calls[0][1] is cmd
    assert spy_e.calls[0][2] is engine


def test_ce06b_engine_reached_exactly_once():
    spy_e = _ExecuteSpy()
    state = OrderState()
    compose_command_execution(
        CallerResult(query=None, command=_valid_operation_result()),
        state,
        OrderEngine(),
        to_resolved_operation_fn=_BoundarySpy(),
        execute_resolution_fn=spy_e,
    )
    assert len(spy_e.calls) == 1


# =============================================
# CE-07 — state identity preserved (in-place mutation)
# =============================================

def test_ce07_executed_returns_same_state_object():
    state = OrderState()
    result = compose_command_execution(
        CallerResult(query=None, command=_valid_operation_result()),
        state,
        OrderEngine(),
    )
    assert result.status is CommandExecutionStatus.EXECUTED
    assert result.state is state


# =============================================
# CE-08 — mutation visible in returned state
# =============================================

def test_ce08_mutation_visible():
    state = OrderState()
    result = compose_command_execution(
        CallerResult(query=None, command=_valid_operation_result()),
        state,
        OrderEngine(),
    )
    assert result.status is CommandExecutionStatus.EXECUTED
    assert len(result.state.items) == 1
    assert result.state.items[0].product_id == "SKU-PROV"
    assert "ITEM_ADDED" in result.events


# =============================================
# CE-09 — events == [] does NOT change status
# =============================================

def test_ce09_empty_events_does_not_change_status():
    state = OrderState()
    fake = _FakeExecute(events=[])
    result = compose_command_execution(
        CallerResult(query=None, command=_valid_operation_result()),
        state,
        OrderEngine(),
        to_resolved_operation_fn=_BoundarySpy(),
        execute_resolution_fn=fake,
    )
    assert result.status is CommandExecutionStatus.EXECUTED
    assert result.events == ()


# =============================================
# CE-10 — defensive engine rejection does not change status
# =============================================

def test_ce10_defensive_rejection_stays_executed():
    state = OrderState()
    fake = _FakeExecute(events=["some_error"])
    result = compose_command_execution(
        CallerResult(query=None, command=_valid_operation_result()),
        state,
        OrderEngine(),
        to_resolved_operation_fn=_BoundarySpy(),
        execute_resolution_fn=fake,
    )
    assert result.status is CommandExecutionStatus.EXECUTED
    assert result.events == ("some_error",)


# =============================================
# CE-11 — QUERY side never processed
# =============================================

def _query_result():
    return QueryResolutionResult(
        status=QueryResolutionStatus.PRODUCT_NOT_FOUND,
        query_type=QueryType.QUERY_PRICE,
        product_id=None,
        reason_code="TEST",
        evidence=[],
    )


def test_ce11_query_only_yields_not_invoked():
    spy_b = _BoundarySpy()
    spy_e = _ExecuteSpy()
    result = compose_command_execution(
        CallerResult(query=_query_result(), command=None),
        OrderState(),
        OrderEngine(),
        to_resolved_operation_fn=spy_b,
        execute_resolution_fn=spy_e,
    )
    assert result.status is CommandExecutionStatus.NOT_INVOKED
    assert spy_b.calls == []
    assert spy_e.calls == []


def test_ce11b_query_coexisting_is_untouched():
    qr = _query_result()
    cmd = _valid_operation_result()
    caller_result = CallerResult(query=qr, command=cmd)
    state = OrderState()
    result = compose_command_execution(
        caller_result, state, OrderEngine()
    )
    assert result.status is CommandExecutionStatus.EXECUTED
    assert caller_result.query is qr
    assert caller_result.command is cmd


# =============================================
# CE-12 — no legacy dependencies
# =============================================

_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "enum",
    "typing",
    "order.engine",
    "order.execution",
    "order.resolution_boundary",
    "order.resolution_result",
    "order.state",
    "pipeline.application_caller",
}


def test_ce12_imports_only_expected():
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


def test_ce12b_no_legacy_references_in_code():
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
        "ConversationProcessor",
        "HybridPipeline",
        "hybrid_v1",
        "hybrid_v2",
        "ModularAdapter",
        "catalog_retriever",
        "product_resolver",
        "resolve_operation",
        "resolve_query",
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


def test_ce12c_no_direct_engine_apply_call():
    """Composition must go through execute_resolution, never engine.apply directly."""
    source = _MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "apply":
                pytest.fail(
                    f"direct .apply() call at line {node.lineno}"
                )


# =============================================
# CE-13 — determinism
# =============================================

def test_ce13_determinism():
    state = OrderState()
    cmd = _valid_operation_result()
    caller_result = CallerResult(query=None, command=cmd)
    outcomes = []
    for _ in range(5):
        state = OrderState()
        r = compose_command_execution(caller_result, state, OrderEngine())
        outcomes.append((r.status, len(r.state.items), r.events))
    assert all(o == outcomes[0] for o in outcomes)


# =============================================
# CE-14 — E2E through application_caller
# =============================================

def test_ce14_e2e_message_to_orderstate_mutation():
    """
    End-to-end demonstration of the closed gap:

        message -> application_caller.invoke -> CallerResult
                -> compose_command_execution
                -> execute_resolution -> OrderEngine
                -> OrderState updated
    """
    message = "adiciona 5kg de provolone"
    observation = SignalObservation(
        query=None,
        command=CommandObservation(evidence=CommandEvidence.PRESENT),
    )
    plan = DispatchPlan(decisions=(
        DispatchDecision(
            DispatchTarget.QUERY, DispatchAction.NO_DISPATCH_NO_OBSERVATION
        ),
        DispatchDecision(
            DispatchTarget.COMMAND, DispatchAction.DISPATCH
        ),
    ))
    state = OrderState()
    engine = OrderEngine()

    def fake_resolve_operation(msg, st):
        return _valid_operation_result()

    caller_result = invoke(
        message, observation, plan, state,
        resolve_operation_fn=fake_resolve_operation,
    )
    assert caller_result.command is not None

    execution = compose_command_execution(caller_result, state, engine)

    assert execution.status is CommandExecutionStatus.EXECUTED
    assert execution.state is state
    assert len(state.items) == 1
    assert state.items[0].product_id == "SKU-PROV"
    assert state.items[0].product_term == "provolone"
    assert "ITEM_ADDED" in execution.events