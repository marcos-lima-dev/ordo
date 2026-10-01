"""
Telegram Controlled Execution v1 — supervised harness.

Connects the existing Telegram path (transport + adapter) to the
canonical execution path (orchestrate_command and its composition
chain), restricted to explicitly authorized chats and gated by an
explicit boolean kill switch. Additionally closes the conversation
loop by delivering a minimal, truthful response to the origin chat.

The harness does NOT:
    - produce external commercial side effects (ERP, billing, stock,
      logistics, payment, external order emission);
    - duplicate transport / adapter / mapping / session / idempotency
      responsibilities;
    - bypass CommandSafetyGuard;
    - alter OrderState directly (the canonical path does, via the
      composition chain);
    - implement a second allowlist (the adapter's allowlist is REUSE);
    - interpret outcomes beyond mapping them to a minimal, truthful
      response.

The allowlist is the adapter's. A chat outside the adapter allowlist
never reaches this harness with a success ParseStatus, and therefore
never reaches execution.

Composition (semantic, not literal wiring order):
    Safety  →  PA-1 Authority (when applied)  →  resolution

Safety is mandatory. PA-1 Authority is compositional and optional.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, List, Optional, Tuple

from order.engine import OrderEngine

from pipeline.application_orchestrator import (
    OrchestrationOutcome,
    orchestrate_command,
)
from pipeline.application_processing import ApplicationProcessor
from pipeline.conversation_mapping import InMemoryConversationMappingStore
from pipeline.conversation_session import InMemoryConversationSessionStore
from pipeline.idempotency import InMemoryIdempotencyStore
from pipeline.telegram_adapter import TelegramAdapter
from pipeline.telegram_response import compose_response
from pipeline.telegram_transport import TelegramTransport, next_offset


# Values of ParseStatus that mean "successfully parsed".
_PARSE_SUCCESS_STATUSES = frozenset({"OK", "PARSED"})


class ExecutionOutcome(Enum):
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    EXECUTION_DISABLED = "EXECUTION_DISABLED"
    DUPLICATE = "DUPLICATE"
    SAFETY_BLOCKED = "SAFETY_BLOCKED"
    CLARIFICATION = "CLARIFICATION"
    EXECUTED = "EXECUTED"
    ERROR = "ERROR"


@dataclass(frozen=True)
class UpdateOutcome:
    update_id: Optional[int]
    outcome: ExecutionOutcome
    reason: Optional[str] = None


class TelegramControlledExecution:
    """
    Minimal harness: Telegram update → canonical execution path →
    minimal response delivery.

    Dependencies are injected. The harness composes; it does not
    duplicate. `execution_enabled` is the kill switch: when False,
    no Telegram message can reach OrderState mutation.
    """

    def __init__(
        self,
        *,
        transport: TelegramTransport,
        adapter: TelegramAdapter,
        processor: ApplicationProcessor,
        engine: OrderEngine,
        session_store: InMemoryConversationSessionStore,
        idempotency_store: InMemoryIdempotencyStore,
        mapping_store: InMemoryConversationMappingStore,
        resolve_operation_fn: Callable,
        execution_enabled: bool,
    ) -> None:
        self._transport = transport
        self._adapter = adapter
        self._processor = processor
        self._engine = engine
        self._session_store = session_store
        self._idempotency_store = idempotency_store
        self._mapping_store = mapping_store
        self._resolve_operation_fn = resolve_operation_fn
        self._execution_enabled = bool(execution_enabled)

    @property
    def execution_enabled(self) -> bool:
        return self._execution_enabled

    def run_once(self, offset: int = 0) -> Tuple[int, List[UpdateOutcome]]:
        """
        Poll the transport once. Process each update. Deliver a
        minimal response when applicable. Return (next_offset, outcomes).

        Transport-level failure propagates; per-update failure is
        captured as ExecutionOutcome.ERROR.
        """
        updates = self._transport.get_updates(offset)
        results = [self._process_one(u) for u in updates]

        outcomes: List[UpdateOutcome] = []
        for outcome, destination in results:
            outcomes.append(outcome)
            self._deliver(outcome, destination)

        new_offset = next_offset(updates)
        return (new_offset if new_offset is not None else offset), outcomes

    # ---------- internal ----------

    def _deliver(
        self, outcome: UpdateOutcome, destination: Optional[str],
    ) -> None:
        """
        Compose and deliver a minimal response, if applicable.

        Delivery failure does not propagate: the execution outcome is
        not invalidated by a transport-level send failure.
        """
        response = compose_response(outcome.outcome.name, destination=destination)
        if response is None:
            return
        try:
            self._transport.send_message(response.destination, response.text)
        except Exception:
            # v1: send failures are silent. A future stage may add
            # delivery observability; not in scope here.
            pass

    def _process_one(
        self, update: Any,
    ) -> Tuple[UpdateOutcome, Optional[str]]:
        update_id = update.get("update_id") if isinstance(update, dict) else None

        try:
            parse_result = self._adapter.parse(update)
        except Exception as e:
            return (
                UpdateOutcome(
                    update_id, ExecutionOutcome.ERROR,
                    f"adapter: {type(e).__name__}: {e}",
                ),
                None,
            )

        status_name = getattr(parse_result.status, "name", None)
        if status_name not in _PARSE_SUCCESS_STATUSES:
            reason = getattr(parse_result, "reason", None) or \
                     getattr(parse_result.status, "value", None)
            return (
                UpdateOutcome(update_id, ExecutionOutcome.NOT_ELIGIBLE, reason),
                None,
            )

        channel_identity, external_message_id, text = _extract_parsed(parse_result)
        if channel_identity is None or external_message_id is None or text is None:
            return (
                UpdateOutcome(
                    update_id, ExecutionOutcome.ERROR,
                    "parse succeeded but parsed fields incomplete",
                ),
                None,
            )

        destination = getattr(channel_identity, "external_conversation_id", None)

        if not self._execution_enabled:
            return (
                UpdateOutcome(update_id, ExecutionOutcome.EXECUTION_DISABLED),
                destination,
            )

        try:
            processing = self._processor.process(text)
        except Exception as e:
            return (
                UpdateOutcome(
                    update_id, ExecutionOutcome.ERROR,
                    f"processor: {type(e).__name__}: {e}",
                ),
                destination,
            )

        conversation_id = self._mapping_store.get_or_create(channel_identity)

        try:
            orchestration = orchestrate_command(
                conversation_id=conversation_id,
                external_message_id=external_message_id,
                message=text,
                observation=processing.observation,
                dispatch_plan=processing.dispatch_plan,
                engine=self._engine,
                session_store=self._session_store,
                idempotency_store=self._idempotency_store,
                resolve_operation_fn=self._resolve_operation_fn,
            )
        except Exception as e:
            return (
                UpdateOutcome(
                    update_id, ExecutionOutcome.ERROR,
                    f"orchestrate: {type(e).__name__}: {e}",
                ),
                destination,
            )

        return (
            UpdateOutcome(
                update_id, _classify(orchestration), _reason_from(orchestration),
            ),
            destination,
        )


# ---------- module helpers ----------

def _extract_parsed(parse_result):
    """
    Return (channel_identity, external_message_id, text) from a
    ParseResult whose `.message` field carries the parsed payload.
    Returns (None, None, None) if the payload is absent.
    """
    parsed = getattr(parse_result, "message", None)
    if parsed is None:
        return (None, None, None)
    return (
        getattr(parsed, "channel_identity", None),
        getattr(parsed, "external_message_id", None),
        getattr(parsed, "text", None),
    )


def _classify(orchestration) -> ExecutionOutcome:
    if orchestration.outcome is OrchestrationOutcome.ALREADY_CLAIMED:
        return ExecutionOutcome.DUPLICATE

    cmd = orchestration.caller_result.command if orchestration.caller_result else None
    if cmd is not None:
        reason = getattr(cmd, "reason_code", None)
        if reason == "REPRESENTATIONAL_OVERFLOW":
            return ExecutionOutcome.SAFETY_BLOCKED
        outcome = getattr(cmd, "outcome", None)
        outcome_name = getattr(outcome, "name", None)
        if outcome_name == "NEEDS_CLARIFICATION":
            return ExecutionOutcome.CLARIFICATION

    if orchestration.execution_result is not None:
        return ExecutionOutcome.EXECUTED

    return ExecutionOutcome.CLARIFICATION


def _reason_from(orchestration) -> Optional[str]:
    cmd = orchestration.caller_result.command if orchestration.caller_result else None
    if cmd is None:
        return None
    return getattr(cmd, "reason_code", None)