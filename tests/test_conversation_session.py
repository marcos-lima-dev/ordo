import ast
import sys
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from order.engine import OrderEngine
from order.resolution_result import OutcomeType, ResolutionResult
from order.state import OrderState

from pipeline.application_caller import invoke
from pipeline.command_execution import compose_command_execution
from pipeline.conversation_session import (
    ConversationId,
    InMemoryConversationSessionStore,
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
    Path(__file__).parent.parent / "pipeline" / "conversation_session.py"
)


# =============================================
# helpers
# =============================================

def _cid(value: str) -> ConversationId:
    return ConversationId(value=value)


def _command_plan():
    return DispatchPlan(decisions=(
        DispatchDecision(
            DispatchTarget.QUERY, DispatchAction.NO_DISPATCH_NO_OBSERVATION
        ),
        DispatchDecision(
            DispatchTarget.COMMAND, DispatchAction.DISPATCH
        ),
    ))


def _command_observation():
    return SignalObservation(
        query=None,
        command=CommandObservation(evidence=CommandEvidence.PRESENT),
    )


def _add_item_op(product_id, product_term, qty=1.0, unit=None):
    return ResolutionResult(
        outcome=OutcomeType.OPERATION,
        operation={
            "type": "ADD_ITEM",
            "product_id": product_id,
            "product_term": product_term,
            "quantity_value": qty,
            "quantity_unit": unit,
            "target_item_id": None,
            "replacement_product_id": None,
        },
        evidence=[],
    )


def _fake_resolver(message, state):
    msg = message.lower()
    if "provolone" in msg:
        return _add_item_op("CQ-46", "provolone")
    if "brie" in msg:
        return _add_item_op("CQ-47", "brie")
    if "gorgonzola" in msg:
        return _add_item_op("CQ-48", "gorgonzola")
    return ResolutionResult(outcome=OutcomeType.NO_OP)


def _turn(store, engine, cid, message):
    state = store.get_or_create(cid)
    caller_result = invoke(
        message,
        _command_observation(),
        _command_plan(),
        state,
        resolve_operation_fn=_fake_resolver,
    )
    execution = compose_command_execution(caller_result, state, engine)
    store.save(cid, execution.state if execution.state is not None else state)
    return state


# =============================================
# AST checker for forbidden symbols (test-only)
# =============================================

_FORBIDDEN_TOKENS = (
    "OrderEngine",
    "add_item",
    "remove_item",
    "ResolutionResult",
    "resolve_operation",
    "application_caller",
)


def _collect_docstring_node_ids(tree):
    ids = set()
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
                ids.add(id(node.body[0].value))
    return ids


def _assert_no_forbidden_in_code(source: str) -> None:
    """
    Raise AssertionError if any forbidden symbol appears in code
    (non-docstring string constants, imports by module OR by symbol
    name, or direct .apply calls).
    """
    tree = ast.parse(source)
    docstring_ids = _collect_docstring_node_ids(tree)

    # 1. Non-docstring string constants must not contain forbidden tokens.
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstring_ids
        ):
            for token in _FORBIDDEN_TOKENS:
                assert token not in node.value, (
                    f"non-docstring string references {token!r}: "
                    f"{node.value!r}"
                )

    # 2. Imports must not reference forbidden tokens, in the module
    #    path OR in the imported symbol name.
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for token in _FORBIDDEN_TOKENS:
                assert token not in module, (
                    f"imports forbidden module {token!r}: {module!r}"
                )
            for alias in node.names:
                for token in _FORBIDDEN_TOKENS:
                    assert token not in alias.name, (
                        f"imports forbidden symbol {token!r}: "
                        f"{alias.name!r}"
                    )
        if isinstance(node, ast.Import):
            for alias in node.names:
                for token in _FORBIDDEN_TOKENS:
                    assert token not in alias.name, (
                        f"imports forbidden {token!r}: {alias.name!r}"
                    )

    # 3. No direct .apply() calls.
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "apply":
            raise AssertionError(
                f"direct .apply() call at line {node.lineno}"
            )


# =============================================
# CS-01 — ConversationId type
# =============================================

def test_cs01_conversation_id_has_only_value_field():
    field_names = {f.name for f in fields(ConversationId)}
    assert field_names == {"value"}


def test_cs01b_conversation_id_is_frozen():
    cid = _cid("a")
    with pytest.raises(FrozenInstanceError):
        cid.value = "b"


def test_cs01c_no_channel_specific_fields():
    field_names = {f.name for f in fields(ConversationId)}
    for forbidden in (
        "telegram", "whatsapp", "chat_id", "phone", "user_id",
        "channel", "provider",
    ):
        assert forbidden not in field_names


# =============================================
# CS-02 — get_or_create semantics
# =============================================

def test_cs02_first_access_creates_empty_state():
    store = InMemoryConversationSessionStore()
    state = store.get_or_create(_cid("conv-a"))
    assert isinstance(state, OrderState)
    assert state.items == []


def test_cs02b_second_access_returns_same_state():
    store = InMemoryConversationSessionStore()
    a1 = store.get_or_create(_cid("conv-a"))
    a2 = store.get_or_create(_cid("conv-a"))
    assert a1 is a2


def test_cs02c_different_ids_produce_distinct_states():
    store = InMemoryConversationSessionStore()
    a = store.get_or_create(_cid("conv-a"))
    b = store.get_or_create(_cid("conv-b"))
    assert a is not b


# =============================================
# CS-03 — save semantics
# =============================================

def test_cs03_save_then_get_returns_saved_state():
    store = InMemoryConversationSessionStore()
    fresh = OrderState()
    store.save(_cid("conv-a"), fresh)
    retrieved = store.get_or_create(_cid("conv-a"))
    assert retrieved is fresh


def test_cs03b_save_does_not_require_prior_get():
    store = InMemoryConversationSessionStore()
    fresh = OrderState()
    store.save(_cid("conv-new"), fresh)
    assert store.get_or_create(_cid("conv-new")) is fresh


# =============================================
# CS-04 — store does not reference commercial execution
# =============================================

def test_cs04_store_does_not_reference_commercial_execution_symbols():
    """
    AST-based check: docstrings may mention forbidden symbols as
    prose, but code must not reference them, import them, or call
    .apply() directly.
    """
    source = _MODULE_PATH.read_text(encoding="utf-8")
    _assert_no_forbidden_in_code(source)


def test_cs04b_ast_check_catches_import_by_symbol_name():
    """Prove the checker detects a forbidden symbol imported by name."""
    synthetic = (
        '"""Docstring may mention OrderEngine."""\n'
        "from order.engine import OrderEngine\n"
    )
    with pytest.raises(AssertionError):
        _assert_no_forbidden_in_code(synthetic)


def test_cs04b2_ast_check_catches_import_by_module_path():
    """Prove the checker detects a forbidden module imported."""
    synthetic = (
        '"""Docstring may mention application_caller."""\n'
        "from pipeline.application_caller import invoke\n"
    )
    with pytest.raises(AssertionError):
        _assert_no_forbidden_in_code(synthetic)


def test_cs04c_ast_check_catches_apply_call():
    """Prove the checker detects a direct .apply() call in code."""
    synthetic = (
        '"""Docstring mentions OrderEngine."""\n'
        "def foo(engine):\n"
        "    engine.apply(None, None)\n"
    )
    with pytest.raises(AssertionError):
        _assert_no_forbidden_in_code(synthetic)


def test_cs04d_ast_check_ignores_docstrings():
    """Prove the checker does not false-positive on docstrings."""
    synthetic = (
        '"""Mentions OrderEngine, add_item, remove_item, ResolutionResult."""\n'
        "def foo():\n"
        "    return 42\n"
    )
    _assert_no_forbidden_in_code(synthetic)


def test_cs04e_store_imports_only_allowed():
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    allowed = {
        "__future__",
        "dataclasses",
        "typing",
        "order.state",
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


# =============================================
# CS-05 — multi-turn E2E (same conversation)
# =============================================

def test_cs05_two_turns_same_conversation_accumulates_items():
    store = InMemoryConversationSessionStore()
    engine = OrderEngine()
    cid = _cid("conv-a")

    _turn(store, engine, cid, "manda o provolone")
    state_after_1 = store.get_or_create(cid)
    assert len(state_after_1.items) == 1
    assert state_after_1.items[0].product_id == "CQ-46"

    _turn(store, engine, cid, "manda o brie")
    state_after_2 = store.get_or_create(cid)
    assert len(state_after_2.items) == 2
    assert {i.product_id for i in state_after_2.items} == {"CQ-46", "CQ-47"}


def test_cs05b_state_carries_same_object_across_turns():
    store = InMemoryConversationSessionStore()
    engine = OrderEngine()
    cid = _cid("conv-a")

    _turn(store, engine, cid, "manda o provolone")
    a1 = store.get_or_create(cid)
    _turn(store, engine, cid, "manda o brie")
    a2 = store.get_or_create(cid)
    assert a1 is a2


# =============================================
# CS-06 — cross-conversation isolation
# =============================================

def test_cs06_cross_conversation_isolation_interleaved():
    store = InMemoryConversationSessionStore()
    engine = OrderEngine()
    cid_a = _cid("conv-a")
    cid_b = _cid("conv-b")

    _turn(store, engine, cid_a, "manda o provolone")
    _turn(store, engine, cid_b, "manda o brie")
    _turn(store, engine, cid_a, "manda o gorgonzola")

    state_a = store.get_or_create(cid_a)
    state_b = store.get_or_create(cid_b)

    a_ids = [i.product_id for i in state_a.items]
    b_ids = [i.product_id for i in state_b.items]

    assert set(a_ids) == {"CQ-46", "CQ-48"}
    assert b_ids == ["CQ-47"]


def test_cs06b_b_never_sees_a_items():
    store = InMemoryConversationSessionStore()
    engine = OrderEngine()
    cid_a = _cid("conv-a")
    cid_b = _cid("conv-b")

    _turn(store, engine, cid_a, "manda o provolone")

    state_b_fresh = store.get_or_create(cid_b)
    assert state_b_fresh.items == []

    _turn(store, engine, cid_b, "manda o brie")
    state_b_final = store.get_or_create(cid_b)
    assert [i.product_id for i in state_b_final.items] == ["CQ-47"]


# =============================================
# CS-07 — determinism
# =============================================

def test_cs07_same_sequence_produces_same_final_state():
    def run():
        store = InMemoryConversationSessionStore()
        engine = OrderEngine()
        cid = _cid("conv-a")
        _turn(store, engine, cid, "manda o provolone")
        _turn(store, engine, cid, "manda o brie")
        return [i.product_id for i in store.get_or_create(cid).items]

    assert run() == run() == run()