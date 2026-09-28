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
    """One full turn: get state, resolve, execute, save."""
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
# CS-04 — store does not mutate commercially
# =============================================

def test_cs04_store_never_calls_add_item():
    """Structural: module must not reference OrderEngine or add_item."""
    source = _MODULE_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "OrderEngine",
        "add_item",
        "remove_item",
        "ResolutionResult",
        "resolve_operation",
        "application_caller",
        "OrderEngine.apply",
    ):
        assert forbidden not in source, (
            f"conversation_session.py must not reference {forbidden!r}"
        )


def test_cs04b_store_imports_only_allowed():
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
    """
    In-memory semantics: same instance across turns for the same
    ConversationId. Identity is NOT part of the contract, but is
    asserted here so future changes must be explicit.
    """
    store = InMemoryConversationSessionStore()
    engine = OrderEngine()
    cid = _cid("conv-a")

    _turn(store, engine, cid, "manda o provolone")
    a1 = store.get_or_create(cid)
    _turn(store, engine, cid, "manda o brie")
    a2 = store.get_or_create(cid)
    assert a1 is a2


# =============================================
# CS-06 — cross-conversation isolation (interleaved A1, B1, A2)
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