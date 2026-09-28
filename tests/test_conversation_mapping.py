import ast
import threading
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from order.engine import OrderEngine
from order.resolution_result import OutcomeType, ResolutionResult
from order.state import OrderState

from pipeline.application_orchestrator import (
    OrchestrationOutcome,
    orchestrate_command,
)
from pipeline.channel_identity import ChannelIdentity
from pipeline.conversation_mapping import InMemoryConversationMappingStore
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
from pipeline.idempotency import (
    ExternalMessageId,
    InMemoryIdempotencyStore,
)
from pipeline.signal_observation import (
    CommandEvidence,
    CommandObservation,
    SignalObservation,
)


_MODULE_PATH = (
    Path(__file__).parent.parent / "pipeline" / "conversation_mapping.py"
)


def _ci(channel, ext_id):
    return ChannelIdentity(channel=channel, external_conversation_id=ext_id)


def _emid(v):
    return ExternalMessageId(value=v)


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


def _add_item(product_id="CQ-46", product_term="provolone"):
    return ResolutionResult(
        outcome=OutcomeType.OPERATION,
        operation={
            "type": "ADD_ITEM",
            "product_id": product_id,
            "product_term": product_term,
            "quantity_value": 1.0,
            "quantity_unit": None,
            "target_item_id": None,
            "replacement_product_id": None,
        },
        evidence=[],
    )


def _resolver(message, state):
    msg = message.lower()
    if "provolone" in msg:
        return _add_item("CQ-46", "provolone")
    if "brie" in msg:
        return _add_item("CQ-47", "brie")
    return ResolutionResult(outcome=OutcomeType.NO_OP)


# =============================================
# AST helper for forbidden-symbol checks (test-only)
# =============================================

_FORBIDDEN = (
    "OrderState",
    "OrderEngine",
    "ResolutionResult",
    "resolve_operation",
    "command_execution",
    "idempotency",
    "application_orchestrator",
)


def _non_docstring_string_constants(tree):
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


def _imported_module_names(tree):
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
    return names


def _imported_symbol_names(tree):
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.name)
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
    return names


# =============================================
# CM-01 — stable mapping
# =============================================

def test_cm01_same_identity_returns_same_conversation():
    store = InMemoryConversationMappingStore()
    ci = _ci("telegram", "12345")
    a = store.get_or_create(ci)
    b = store.get_or_create(ci)
    assert a is b


def test_cm01b_different_identities_distinct():
    store = InMemoryConversationMappingStore()
    a = store.get_or_create(_ci("telegram", "12345"))
    b = store.get_or_create(_ci("telegram", "67890"))
    assert a != b


# =============================================
# CM-02 — channel dimension
# =============================================

def test_cm02_same_external_id_different_channel_distinct():
    store = InMemoryConversationMappingStore()
    tg = store.get_or_create(_ci("telegram", "123"))
    wa = store.get_or_create(_ci("whatsapp", "123"))
    assert tg != wa


# =============================================
# CM-03 — message id independence (P79)
# =============================================

def test_cm03_external_message_id_does_not_participate():
    store = InMemoryConversationMappingStore()
    ci = _ci("telegram", "12345")
    a = store.get_or_create(ci)
    b = store.get_or_create(ci)
    assert a == b


# =============================================
# CM-04 — opaque internal identity
# =============================================

def test_cm04_conversation_id_is_opaque():
    store = InMemoryConversationMappingStore()
    cid = store.get_or_create(_ci("telegram", "12345"))
    assert isinstance(cid, ConversationId)
    assert "telegram" not in cid.value
    assert "12345" not in cid.value


# =============================================
# CM-05 — open channel namespace
# =============================================

@pytest.mark.parametrize(
    "channel",
    ["telegram", "whatsapp", "web", "discord", "email", "sms"],
)
def test_cm05_arbitrary_channel_identifier(channel):
    store = InMemoryConversationMappingStore()
    cid = store.get_or_create(_ci(channel, "abc"))
    assert isinstance(cid, ConversationId)


# =============================================
# CM-06 — diagnostic get
# =============================================

def test_cm06_get_unknown_returns_none():
    store = InMemoryConversationMappingStore()
    assert store.get(_ci("telegram", "12345")) is None


def test_cm06b_get_after_create_returns_same():
    store = InMemoryConversationMappingStore()
    ci = _ci("telegram", "12345")
    cid = store.get_or_create(ci)
    assert store.get(ci) is cid


# =============================================
# CM-07 — concurrency
# =============================================

def test_cm07_concurrent_get_or_create_exactly_one_id():
    store = InMemoryConversationMappingStore()
    ci = _ci("telegram", "12345")
    results = []
    barrier = threading.Barrier(10)

    def worker():
        barrier.wait()
        results.append(store.get_or_create(ci))

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 10
    assert len({r.value for r in results}) == 1


# =============================================
# CM-08 — dependency isolation
# =============================================

def test_cm08_imports_only_allowed():
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    allowed = {
        "__future__",
        "threading",
        "typing",
        "uuid",
        "pipeline.channel_identity",
        "pipeline.conversation_session",
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


def test_cm08b_no_state_or_engine_in_mapping():
    """
    AST-based: docstrings may mention forbidden symbols as prose, but
    code (non-docstring string constants, imports) must not reference
    them.
    """
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))

    for value in _non_docstring_string_constants(tree):
        for token in _FORBIDDEN:
            assert token not in value, (
                f"non-docstring string references {token!r}: {value!r}"
            )

    modules = _imported_module_names(tree)
    symbols = _imported_symbol_names(tree)
    for token in _FORBIDDEN:
        for name in modules | symbols:
            assert token not in name, (
                f"mapping imports forbidden {token!r} via {name!r}"
            )


# =============================================
# CM-09 — E2E local (synthetic channel data)
# =============================================

def test_cm09_e2e_two_messages_same_channel_identity():
    mapping = InMemoryConversationMappingStore()
    sessions = InMemoryConversationSessionStore()
    idem = InMemoryIdempotencyStore()
    engine = OrderEngine()

    ci = _ci("telegram", "12345")

    cid_1 = mapping.get_or_create(ci)
    r1 = orchestrate_command(
        cid_1, _emid("42"), "manda o provolone",
        _command_observation(), _command_plan(),
        engine, sessions, idem,
        resolve_operation_fn=_resolver,
    )
    assert r1.outcome is OrchestrationOutcome.PROCESSED

    cid_2 = mapping.get_or_create(ci)
    assert cid_2 == cid_1

    r2 = orchestrate_command(
        cid_2, _emid("43"), "manda o brie",
        _command_observation(), _command_plan(),
        engine, sessions, idem,
        resolve_operation_fn=_resolver,
    )
    assert r2.outcome is OrchestrationOutcome.PROCESSED

    state = sessions.get_or_create(cid_1)
    assert len(state.items) == 2
    assert {i.product_id for i in state.items} == {"CQ-46", "CQ-47"}


def test_cm09b_e2e_same_channel_different_message_id_isolated_retries():
    mapping = InMemoryConversationMappingStore()
    sessions = InMemoryConversationSessionStore()
    idem = InMemoryIdempotencyStore()
    engine = OrderEngine()

    ci = _ci("telegram", "12345")
    cid = mapping.get_or_create(ci)

    r1 = orchestrate_command(
        cid, _emid("42"), "manda o provolone",
        _command_observation(), _command_plan(),
        engine, sessions, idem,
        resolve_operation_fn=_resolver,
    )
    assert r1.outcome is OrchestrationOutcome.PROCESSED

    r1_retry = orchestrate_command(
        cid, _emid("42"), "manda o provolone",
        _command_observation(), _command_plan(),
        engine, sessions, idem,
        resolve_operation_fn=_resolver,
    )
    assert r1_retry.outcome is OrchestrationOutcome.ALREADY_CLAIMED

    r2 = orchestrate_command(
        cid, _emid("43"), "manda o brie",
        _command_observation(), _command_plan(),
        engine, sessions, idem,
        resolve_operation_fn=_resolver,
    )
    assert r2.outcome is OrchestrationOutcome.PROCESSED

    state = sessions.get_or_create(cid)
    assert len(state.items) == 2