"""
Telegram Controlled Execution v1 — focal tests.

Proves the seven scenarios of the SUCCESS CONDITION in ACTIVE_STAGE.md,
plus structural isolation (no external commercial side effects).
"""
import inspect
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from order.engine import OrderEngine
from order.resolution_result import ResolutionResult, OutcomeType
from order.state import OrderState

from pipeline.channel_identity import ChannelIdentity
from pipeline.command_safety_guard import (
    GuardDecision,
    make_guarded_resolve_operation,
)
from pipeline.conversation_mapping import InMemoryConversationMappingStore
from pipeline.conversation_session import InMemoryConversationSessionStore
from pipeline.dispatch_plan import (
    DispatchAction,
    DispatchDecision,
    DispatchPlan,
    DispatchTarget,
)
from pipeline.idempotency import InMemoryIdempotencyStore
from pipeline.signal_observation import (
    CommandEvidence,
    CommandObservation,
    SignalObservation,
)
from pipeline.telegram_adapter import TelegramAdapter
from pipeline.telegram_execution import (
    ExecutionOutcome,
    TelegramControlledExecution,
)


# ============================================
# Test doubles
# ============================================

class _FakeTransport:
    def __init__(self, updates):
        self._updates = updates

    def get_updates(self, offset=None):
        return list(self._updates)


class _StubProcessor:
    """Returns a minimal ProcessingResult shaped like the real one."""
    def process(self, message):
        observation = SignalObservation(
            query=None,
            command=CommandObservation(evidence=CommandEvidence.PRESENT),
        )
        plan = DispatchPlan(decisions=(
            DispatchDecision(DispatchTarget.QUERY, DispatchAction.NO_DISPATCH_UNRESOLVED),
            DispatchDecision(DispatchTarget.COMMAND, DispatchAction.DISPATCH),
        ))
        return SimpleNamespace(observation=observation, dispatch_plan=plan)


def _stub_guard(decision):
    class _G:
        def check(self, message):
            return SimpleNamespace(decision=decision, evidence=())
    return _G()


def _ok_resolution():
    return ResolutionResult(
        outcome=OutcomeType.OPERATION,
        operation={
            "type": "ADD_ITEM",
            "product_id": "CQ-44",
            "product_term": "CQ-44",
            "quantity_value": 1.0,
            "quantity_unit": "un",
            "target_item_id": None,
            "replacement_product_id": None,
        },
        evidence=["test"],
    )


def _clarification_resolution():
    return ResolutionResult(
        outcome=OutcomeType.NEEDS_CLARIFICATION,
        reason_code="AMBIGUOUS_PRODUCT",
    )


def _authorized_update(update_id=1, message_id=100, chat_id=555, text="manda"):
    return {
        "update_id": update_id,
        "message": {
            "message_id": message_id,
            "chat": {"id": chat_id, "type": "private"},
            "text": text,
        },
    }


def _build_harness(
    *,
    updates,
    execution_enabled=True,
    guard_decision=GuardDecision.SAFE,
    resolve_result=None,
    allowed_chat_ids=(555,),
):
    transport = _FakeTransport(updates)
    adapter = TelegramAdapter(allowed_chat_ids=allowed_chat_ids)
    processor = _StubProcessor()
    engine = OrderEngine()
    session_store = InMemoryConversationSessionStore()
    idempotency_store = InMemoryIdempotencyStore()
    mapping_store = InMemoryConversationMappingStore()

    guard = _stub_guard(guard_decision)
    real_fn_holder = {"calls": 0, "result": resolve_result or _ok_resolution()}

    def _fake_resolve(message, state, *, pre_resolved_product_id=None):
        real_fn_holder["calls"] += 1
        return real_fn_holder["result"]

    guarded = make_guarded_resolve_operation(guard, _fake_resolve)

    harness = TelegramControlledExecution(
        transport=transport,
        adapter=adapter,
        processor=processor,
        engine=engine,
        session_store=session_store,
        idempotency_store=idempotency_store,
        mapping_store=mapping_store,
        resolve_operation_fn=guarded,
        execution_enabled=execution_enabled,
    )
    return {
        "harness": harness,
        "session_store": session_store,
        "mapping_store": mapping_store,
        "real_fn": real_fn_holder,
    }


def _state_for(mapping_store, session_store, chat_id=555):
    cid = mapping_store.get_or_create(ChannelIdentity("telegram", str(chat_id)))
    return session_store.get_or_create(cid)


# ============================================
# 1. Authorized + enabled + executable → OrderState changes
# ============================================

def test_authorized_enabled_executable_mutates_orderstate():
    h = _build_harness(updates=[_authorized_update()])
    _, outcomes = h["harness"].run_once(offset=0)

    assert outcomes[0].outcome is ExecutionOutcome.EXECUTED
    state = _state_for(h["mapping_store"], h["session_store"])
    assert len(state.items) == 1
    assert h["real_fn"]["calls"] == 1


# ============================================
# 2. Kill switch OFF → no mutation
# ============================================

def test_kill_switch_off_no_mutation():
    h = _build_harness(updates=[_authorized_update()], execution_enabled=False)
    _, outcomes = h["harness"].run_once(offset=0)

    assert outcomes[0].outcome is ExecutionOutcome.EXECUTION_DISABLED
    state = _state_for(h["mapping_store"], h["session_store"])
    assert state.items == []
    assert h["real_fn"]["calls"] == 0


# ============================================
# 3. Chat not authorized → no mutation
# ============================================

def test_chat_not_authorized_no_mutation():
    update = _authorized_update(chat_id=999)
    h = _build_harness(updates=[update], allowed_chat_ids=(555,))
    _, outcomes = h["harness"].run_once(offset=0)

    assert outcomes[0].outcome is ExecutionOutcome.NOT_ELIGIBLE
    # No conversation should have been created for the unauthorized chat.
    state = _state_for(h["mapping_store"], h["session_store"], chat_id=999)
    assert state.items == []
    assert h["real_fn"]["calls"] == 0


# ============================================
# 4. Safety block (overflow) → no mutation
# ============================================

def test_safety_block_no_mutation():
    h = _build_harness(
        updates=[_authorized_update()],
        guard_decision=GuardDecision.REPRESENTATIONAL_OVERFLOW,
    )
    _, outcomes = h["harness"].run_once(offset=0)

    assert outcomes[0].outcome is ExecutionOutcome.SAFETY_BLOCKED
    state = _state_for(h["mapping_store"], h["session_store"])
    assert state.items == []
    assert h["real_fn"]["calls"] == 0  # guard short-circuited before real_fn


# ============================================
# 5. Clarification / non-executable → no mutation
# ============================================

def test_clarification_no_mutation():
    h = _build_harness(
        updates=[_authorized_update()],
        resolve_result=_clarification_resolution(),
    )
    _, outcomes = h["harness"].run_once(offset=0)

    assert outcomes[0].outcome is ExecutionOutcome.CLARIFICATION
    state = _state_for(h["mapping_store"], h["session_store"])
    assert state.items == []


# ============================================
# 6. Duplicate ExternalMessageId → single execution
# ============================================

def test_duplicate_does_not_reexecute():
    update = _authorized_update(update_id=1, message_id=100)
    h = _build_harness(updates=[update])
    h["harness"].run_once(offset=0)
    state_after_first = len(_state_for(h["mapping_store"], h["session_store"]).items)

    # Same update again in a fresh transport.
    h["harness"]._transport = _FakeTransport([update])
    _, outcomes2 = h["harness"].run_once(offset=0)

    assert outcomes2[0].outcome is ExecutionOutcome.DUPLICATE
    state_after_second = len(_state_for(h["mapping_store"], h["session_store"]).items)
    assert state_after_second == state_after_first


# ============================================
# 7. No external commercial side effect (AST guard)
# ============================================

def test_no_external_commercial_side_effects():
    import pipeline.telegram_execution as mod
    source = inspect.getsource(mod)
    forbidden_tokens = [
        "requests", "httpx", "aiohttp", "urllib.request", "http.client",
        "smtplib", "imaplib", "poplib",
        "sqlalchemy", "psycopg", "psycopg2", "pymongo", "redis", "sqlite3",
        "boto3", "stripe", "twilio", "sendgrid",
        "subprocess",
    ]
    for token in forbidden_tokens:
        assert token not in source, f"harness must not reference {token}"


# ============================================
# Structural: harness doesn't bypass canonical path
# ============================================

def test_harness_delegates_to_orchestrate_command():
    import pipeline.telegram_execution as mod
    source = inspect.getsource(mod)
    assert "orchestrate_command" in source
    assert "compose_command_execution(" not in source  # not called, only composed upstream
    assert "OrderEngine.apply" not in source           # not called directly
    assert "execute_resolution" not in source          # not called directly
    assert "to_resolved_operation" not in source       # not called directly


def test_harness_reuses_safety_gate_via_composition():
    """
    The harness receives resolve_operation_fn via dependency injection.
    It does not construct its own safety bypass.
    """
    import pipeline.telegram_execution as mod
    source = inspect.getsource(mod)
    assert "CommandSafetyGuard(" not in source
    assert "make_guarded_resolve_operation(" not in source