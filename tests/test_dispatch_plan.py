import ast
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from pipeline.dispatch_plan import (
    DispatchAction,
    DispatchDecision,
    DispatchPlan,
    DispatchTarget,
)


_MODULE_PATH = (
    Path(__file__).parent.parent / "pipeline" / "dispatch_plan.py"
)


# =============================================
# DP-01 — DispatchTarget enum
# =============================================

def test_dp01_target_closed_set():
    assert {t.name for t in DispatchTarget} == {"QUERY", "COMMAND"}


def test_dp01b_target_values():
    assert DispatchTarget.QUERY.value == "QUERY"
    assert DispatchTarget.COMMAND.value == "COMMAND"


# =============================================
# DP-02 — DispatchAction enum
# =============================================

def test_dp02_action_closed_set():
    assert {a.name for a in DispatchAction} == {
        "DISPATCH",
        "NO_DISPATCH_UNRESOLVED",
        "NO_DISPATCH_NOT_QUERY",
        "NO_DISPATCH_ABSENT",
        "NO_DISPATCH_INDETERMINATE",
        "NO_DISPATCH_NO_OBSERVATION",
    }


def test_dp02b_action_excludes_execution_outcomes():
    forbidden = {
        "EXECUTED", "EXECUTABLE", "FAILED", "SUCCESS", "PENDING",
        "AUTHORIZED", "APPROVED", "REJECTED",
    }
    assert forbidden.isdisjoint({a.name for a in DispatchAction})


# =============================================
# DP-03 — DispatchDecision structure
# =============================================

def test_dp03_decision_has_only_target_and_action():
    fields = set(DispatchDecision.__dataclass_fields__.keys())
    assert fields == {"target", "action"}


def test_dp03b_decision_is_frozen():
    d = DispatchDecision(
        target=DispatchTarget.QUERY, action=DispatchAction.DISPATCH
    )
    with pytest.raises(FrozenInstanceError):
        d.action = DispatchAction.NO_DISPATCH_UNRESOLVED


def test_dp03c_no_payload_field():
    fields = set(DispatchDecision.__dataclass_fields__.keys())
    for forbidden in ("payload", "data", "signal", "observation", "intent"):
        assert forbidden not in fields


def test_dp03d_no_priority_or_order_field():
    fields = set(DispatchDecision.__dataclass_fields__.keys())
    for forbidden in ("priority", "order", "ordering", "rank", "sequence"):
        assert forbidden not in fields


def test_dp03e_no_execution_authorization_field():
    fields = set(DispatchDecision.__dataclass_fields__.keys())
    for forbidden in ("is_executable", "authorized", "execute", "may_run"):
        assert forbidden not in fields


# =============================================
# DP-04 — DispatchPlan cardinality (T10-P38)
# =============================================

def _q(action=DispatchAction.DISPATCH):
    return DispatchDecision(target=DispatchTarget.QUERY, action=action)


def _c(action=DispatchAction.DISPATCH):
    return DispatchDecision(target=DispatchTarget.COMMAND, action=action)


def test_dp04_valid_one_query_one_command():
    plan = DispatchPlan(decisions=(_q(), _c()))
    assert len(plan.decisions) == 2


def test_dp04b_reversed_order_also_valid():
    """Tuple order carries no contractual semantics."""
    plan_a = DispatchPlan(decisions=(_q(), _c()))
    plan_b = DispatchPlan(decisions=(_c(), _q()))
    # Both are valid plans; order is physical only.
    assert len(plan_a.decisions) == 2
    assert len(plan_b.decisions) == 2
    targets_a = {d.target for d in plan_a.decisions}
    targets_b = {d.target for d in plan_b.decisions}
    assert targets_a == targets_b == {DispatchTarget.QUERY, DispatchTarget.COMMAND}


def test_dp04c_missing_query_rejected():
    with pytest.raises(ValueError):
        DispatchPlan(decisions=(_c(),))


def test_dp04d_missing_command_rejected():
    with pytest.raises(ValueError):
        DispatchPlan(decisions=(_q(),))


def test_dp04e_duplicate_query_rejected():
    with pytest.raises(ValueError):
        DispatchPlan(decisions=(_q(), _q()))


def test_dp04f_duplicate_command_rejected():
    with pytest.raises(ValueError):
        DispatchPlan(decisions=(_c(), _c()))


def test_dp04g_empty_tuple_rejected():
    with pytest.raises(ValueError):
        DispatchPlan(decisions=())


def test_dp04h_three_decisions_rejected():
    with pytest.raises(ValueError):
        DispatchPlan(decisions=(_q(), _c(), _q()))


def test_dp04i_non_tuple_rejected():
    with pytest.raises(TypeError):
        DispatchPlan(decisions=[_q(), _c()])


def test_dp04j_non_decision_element_rejected():
    with pytest.raises(TypeError):
        DispatchPlan(decisions=("not a decision", _c()))


# =============================================
# DP-05 — DispatchPlan immutability
# =============================================

def test_dp05_plan_is_frozen():
    plan = DispatchPlan(decisions=(_q(), _c()))
    with pytest.raises(FrozenInstanceError):
        plan.decisions = (_q(), _c())


def test_dp05b_plan_has_only_decisions_field():
    fields = set(DispatchPlan.__dataclass_fields__.keys())
    assert fields == {"decisions"}


def test_dp05c_no_execution_authorization_field_on_plan():
    fields = set(DispatchPlan.__dataclass_fields__.keys())
    for forbidden in (
        "is_execution_authorization",
        "is_executable",
        "authorized",
        "execute",
    ):
        assert forbidden not in fields


def test_dp05d_no_observation_field_on_plan():
    fields = set(DispatchPlan.__dataclass_fields__.keys())
    for forbidden in ("observation", "signal_observation", "observations"):
        assert forbidden not in fields


# =============================================
# DP-06 — Independent actions coexist (T10-P25 symmetry)
# =============================================

def test_dp06_query_unresolved_with_command_dispatch():
    plan = DispatchPlan(
        decisions=(
            _q(DispatchAction.NO_DISPATCH_UNRESOLVED),
            _c(DispatchAction.DISPATCH),
        )
    )
    by_target = {d.target: d.action for d in plan.decisions}
    assert by_target[DispatchTarget.QUERY] is DispatchAction.NO_DISPATCH_UNRESOLVED
    assert by_target[DispatchTarget.COMMAND] is DispatchAction.DISPATCH


def test_dp06b_command_indeterminate_with_query_dispatch():
    plan = DispatchPlan(
        decisions=(
            _q(DispatchAction.DISPATCH),
            _c(DispatchAction.NO_DISPATCH_INDETERMINATE),
        )
    )
    by_target = {d.target: d.action for d in plan.decisions}
    assert by_target[DispatchTarget.QUERY] is DispatchAction.DISPATCH
    assert by_target[DispatchTarget.COMMAND] is DispatchAction.NO_DISPATCH_INDETERMINATE


def test_dp06c_both_dispatch():
    plan = DispatchPlan(
        decisions=(_q(DispatchAction.DISPATCH), _c(DispatchAction.DISPATCH))
    )
    assert all(
        d.action is DispatchAction.DISPATCH for d in plan.decisions
    )


def test_dp06d_both_no_observation():
    plan = DispatchPlan(
        decisions=(
            _q(DispatchAction.NO_DISPATCH_NO_OBSERVATION),
            _c(DispatchAction.NO_DISPATCH_NO_OBSERVATION),
        )
    )
    assert all(
        d.action is DispatchAction.NO_DISPATCH_NO_OBSERVATION
        for d in plan.decisions
    )


def test_dp06e_no_dispatch_absent_only_in_absence_of_positive():
    """
    NO_DISPATCH_ABSENT is a coordination state, not an execution outcome.
    """
    plan = DispatchPlan(
        decisions=(
            _q(DispatchAction.DISPATCH),
            _c(DispatchAction.NO_DISPATCH_ABSENT),
        )
    )
    by_target = {d.target: d.action for d in plan.decisions}
    assert by_target[DispatchTarget.COMMAND] is DispatchAction.NO_DISPATCH_ABSENT


# =============================================
# DP-07 — Order carries no semantics
# =============================================

def test_dp07_order_does_not_affect_validation():
    plan_qc = DispatchPlan(decisions=(_q(), _c()))
    plan_cq = DispatchPlan(decisions=(_c(), _q()))
    # Both are valid. The only difference is physical tuple order.
    assert {d.target for d in plan_qc.decisions} == {d.target for d in plan_cq.decisions}


def test_dp07b_no_order_or_priority_field_in_source():
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            assert node.target.id not in (
                "priority", "order", "ordering", "rank", "sequence",
            ), f"field {node.target.id!r} is forbidden"


# =============================================
# DP-08 — Dependency isolation
# =============================================

def test_dp08_imports_only_allowed_modules():
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    allowed = {"__future__", "dataclasses", "enum", "typing"}
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


def test_dp08b_no_forbidden_symbols_in_source():
    source = _MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    # Non-docstring string constants must not contain forbidden tokens.
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

    forbidden_tokens = (
        "SignalObservation",
        "QueryIntentSignal",
        "CommandEvidence",
        "SemanticIntent",
        "OperationType",
        "QueryType",
        "CommandLabel",
        "OrderState",
        "OrderEngine",
        "resolve_operation",
        "resolve_query",
        "execute_resolution",
        "ModularAdapter",
        "CommandRecognizer",
        "QueryIntentProvider",
        "QueryIntentBootstrap",
    )
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstring_ids
        ):
            for token in forbidden_tokens:
                assert token not in node.value, (
                    f"non-docstring string references {token!r}: "
                    f"{node.value!r}"
                )


# =============================================
# DP-09 — No pipeline/function references in decisions
# =============================================

def test_dp09_target_values_are_domain_names_not_function_names():
    for t in DispatchTarget:
        assert t.value.isupper()
        assert "(" not in t.value
        assert "." not in t.value


def test_dp09b_no_callable_fields():
    """
    No dataclass field may be typed as Callable. Structural check
    via AST — does not require instantiating the dataclasses.
    """
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if node.name not in ("DispatchDecision", "DispatchPlan"):
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign):
                ann = stmt.annotation
                if isinstance(ann, ast.Name):
                    assert ann.id != "Callable", (
                        f"field {stmt.target.id!r} in {node.name} "
                        f"typed as Callable"
                    )
                if isinstance(ann, ast.Subscript):
                    if isinstance(ann.value, ast.Name):
                        assert ann.value.id != "Callable", (
                            f"field {stmt.target.id!r} in {node.name} "
                            f"typed as Callable"
                        )
