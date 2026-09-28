import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from order.engine import OrderEngine
from order.resolution_result import OutcomeType, ResolutionResult
from order.state import OrderState

from pipeline.application_orchestrator import (
    OrchestrationOutcome,
    OrchestrationResult,
    orchestrate_command,
)
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
    IdempotencyKey,
    InMemoryIdempotencyStore,
)
from pipeline.signal_observation import (
    CommandEvidence,
    CommandObservation,
    SignalObservation,
)


_MODULE_PATH = (
    Path(__file__).parent.parent
    / "pipeline"
    / "application_orchestrator.py"
)


# =============================================
# helpers
# =============================================

def _cid(v):
    return ConversationId(value=v)


def _emid(v):
    return ExternalMessageId(value=v)


def _command_only_plan():
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


def _clarification_resolver(message, state):
    return ResolutionResult(
        outcome=OutcomeType.NEEDS_CLARIFICATION,
        reason_code="REPRESENTATIONAL_OVERFLOW",
    )


def _raising_resolver(message, state):
    raise RuntimeError("boom")


def _setup():
    return (
        InMemoryConversationSessionStore(),
        InMemoryIdempotencyStore(),
        OrderEngine(),
    )


# =============================================
# AO-01 — first delivery processed
# =============================================

def test_ao01_first_delivery_processed():
    sessions, idem, engine = _setup()
    cid = _cid("A")
    emid = _emid("42")

    result = orchestrate_command(
        cid, emid, "manda o provolone",
        _command_observation(), _command_only_plan(),
        engine, sessions, idem,
        resolve_operation_fn=_resolver,
    )

    assert result.outcome is OrchestrationOutcome.PROCESSED
    assert result.caller_result is not None
    assert result.execution_result is not None
    assert sessions.get_or_create(cid).items[0].product_id == "CQ-46"


# =============================================
# AO-02 — retry same identity: no re-execution
# =============================================

def test_ao02_retry_same_identity_no_re_execution():
    sessions, idem, engine = _setup()
    cid = _cid("A")
    emid = _emid("42")

    orchestrate_command(
        cid, emid, "manda o provolone",
        _command_observation(), _command_only_plan(),
        engine, sessions, idem,
        resolve_operation_fn=_resolver,
    )
    # capture state, engine effects
    state_after_first = sessions.get_or_create(cid)
    items_first = list(state_after_first.items)

    result = orchestrate_command(
        cid, emid, "manda o provolone",
        _command_observation(), _command_only_plan(),
        engine, sessions, idem,
        resolve_operation_fn=_resolver,
    )

    assert result.outcome is OrchestrationOutcome.ALREADY_CLAIMED
    assert result.previous_completed is True
    assert result.caller_result is None
    assert result.execution_result is None

    state_after_second = sessions.get_or_create(cid)
    assert state_after_second.items == items_first
    assert len(state_after_second.items) == 1


# =============================================
# AO-03 — same text, different message id
# =============================================

def test_ao03_same_text_different_message_id_processes_twice():
    sessions, idem, engine = _setup()
    cid = _cid("A")

    orchestrate_command(
        cid, _emid("42"), "manda o provolone",
        _command_observation(), _command_only_plan(),
        engine, sessions, idem,
        resolve_operation_fn=_resolver,
    )
    orchestrate_command(
        cid, _emid("43"), "manda o provolone",
        _command_observation(), _command_only_plan(),
        engine, sessions, idem,
        resolve_operation_fn=_resolver,
    )

    state = sessions.get_or_create(cid)
    assert len(state.items) == 2


# =============================================
# AO-04 — same message id, different conversation
# =============================================

def test_ao04_same_message_id_different_conversation():
    sessions, idem, engine = _setup()

    r_a = orchestrate_command(
        _cid("A"), _emid("42"), "manda o provolone",
        _command_observation(), _command_only_plan(),
        engine, sessions, idem,
        resolve_operation_fn=_resolver,
    )
    r_b = orchestrate_command(
        _cid("B"), _emid("42"), "manda o provolone",
        _command_observation(), _command_only_plan(),
        engine, sessions, idem,
        resolve_operation_fn=_resolver,
    )

    assert r_a.outcome is OrchestrationOutcome.PROCESSED
    assert r_b.outcome is OrchestrationOutcome.PROCESSED

    a_items = sessions.get_or_create(_cid("A")).items
    b_items = sessions.get_or_create(_cid("B")).items
    assert len(a_items) == 1
    assert len(b_items) == 1
    # distinct objects
    assert sessions.get_or_create(_cid("A")) is not sessions.get_or_create(_cid("B"))


# =============================================
# AO-05 — claimed but not completed
# =============================================

def test_ao05_claimed_but_incomplete_not_replayed_not_completed():
    sessions, idem, engine = _setup()
    cid = _cid("A")
    emid = _emid("42")
    key = IdempotencyKey(cid, emid)

    # pre-claim manually (simulating an interrupted attempt)
    idem.claim(key)

    result = orchestrate_command(
        cid, emid, "manda o provolone",
        _command_observation(), _command_only_plan(),
        engine, sessions, idem,
        resolve_operation_fn=_resolver,
    )

    assert result.outcome is OrchestrationOutcome.ALREADY_CLAIMED
    assert result.previous_completed is False
    assert result.caller_result is None
    assert sessions.get_or_create(cid).items == []


# =============================================
# AO-06 — exception after claim
# =============================================

def test_ao06_exception_leaves_claim_incomplete_and_propagates():
    sessions, idem, engine = _setup()
    cid = _cid("A")
    emid = _emid("42")
    key = IdempotencyKey(cid, emid)

    with pytest.raises(RuntimeError, match="boom"):
        orchestrate_command(
            cid, emid, "manda o provolone",
            _command_observation(), _command_only_plan(),
            engine, sessions, idem,
            resolve_operation_fn=_raising_resolver,
        )

    rec = idem.get(key)
    assert rec is not None
    assert rec.claimed is True
    assert rec.completed is False

    # retry: should not re-execute
    result = orchestrate_command(
        cid, emid, "manda o provolone",
        _command_observation(), _command_only_plan(),
        engine, sessions, idem,
        resolve_operation_fn=_resolver,
    )
    assert result.outcome is OrchestrationOutcome.ALREADY_CLAIMED
    assert result.previous_completed is False


# =============================================
# AO-07 — clarification retry
# =============================================

def test_ao07_clarification_retry_no_new_commercial_processing():
    sessions, idem, engine = _setup()
    cid = _cid("A")
    emid = _emid("42")

    first = orchestrate_command(
        cid, emid, "manda provolone e brie",
        _command_observation(), _command_only_plan(),
        engine, sessions, idem,
        resolve_operation_fn=_clarification_resolver,
    )
    assert first.outcome is OrchestrationOutcome.PROCESSED
    assert first.caller_result.command.outcome is OutcomeType.NEEDS_CLARIFICATION
    assert sessions.get_or_create(cid).items == []

    second = orchestrate_command(
        cid, emid, "manda provolone e brie",
        _command_observation(), _command_only_plan(),
        engine, sessions, idem,
        resolve_operation_fn=_clarification_resolver,
    )
    assert second.outcome is OrchestrationOutcome.ALREADY_CLAIMED
    assert second.previous_completed is True


# =============================================
# AO-08 — result shape
# =============================================

def test_ao08_result_fields():
    assert {f.name for f in OrchestrationResult.__dataclass_fields__.values()} == {
        "outcome", "previous_completed", "caller_result", "execution_result",
    }


def test_ao08b_outcome_enum():
    assert {o.name for o in OrchestrationOutcome} == {
        "PROCESSED", "ALREADY_CLAIMED",
    }


# =============================================
# AO-09 — dependency isolation
# =============================================

def test_ao09_imports_only_allowed():
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    allowed = {
        "__future__",
        "dataclasses",
        "enum",
        "typing",
        "order.engine",
        "order.state",
        "pipeline.application_caller",
        "pipeline.command_execution",
        "pipeline.conversation_session",
        "pipeline.dispatch_plan",
        "pipeline.idempotency",
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