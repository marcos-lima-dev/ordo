"""
ORDO — Application orchestrator (idempotency stage).

Coordinates idempotent COMMAND processing:

    claim
    -> load state
    -> canonical application caller
    -> canonical command execution
    -> save state
    -> complete

The orchestrator owns delivery concerns (claim/complete) and
delegation. It does NOT own resolution, resolution semantics, or
engine logic.

Principles honored:
    P45  APPLICATION CALLER INVOKES; IT DOES NOT RESOLVE OR EXECUTE
    P69  CONVERSATION BOUNDARY RESOLVES IDENTITY; SESSION STORE OWNS STATE
    P70  SESSION STORE PRESERVES STATE; DOMAIN EXECUTION MUTATES COMMERCIAL STATE
    P75  IDEMPOTENCY CLAIM IS ATOMIC BY CONTRACT
    P76  CLAIMED != COMPLETED
    P77  UNCERTAIN EXECUTION MUST NOT BE SILENTLY REPLAYED OR REPORTED AS COMPLETED

This module does NOT:
    - recognize language;
    - resolve product, quantity, or operation;
    - mutate OrderState directly (OrderEngine does, via the canonical path);
    - know Telegram, WhatsApp, or any provider;
    - implement retry, lease, or recovery.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from order.engine import OrderEngine
from order.state import OrderState

from pipeline.application_caller import CallerResult, invoke
from pipeline.command_execution import (
    CommandExecutionResult,
    compose_command_execution,
)
from pipeline.conversation_session import (
    ConversationId,
    InMemoryConversationSessionStore,
)
from pipeline.dispatch_plan import DispatchPlan
from pipeline.idempotency import (
    ClaimStatus,
    ExternalMessageId,
    IdempotencyKey,
    InMemoryIdempotencyStore,
)
from pipeline.resolution_pipeline import resolve_operation
from pipeline.signal_observation import SignalObservation


class OrchestrationOutcome(Enum):
    PROCESSED = "PROCESSED"
    ALREADY_CLAIMED = "ALREADY_CLAIMED"


@dataclass(frozen=True)
class OrchestrationResult:
    """
    Result of one orchestration call.

    outcome == PROCESSED:
        caller_result and execution_result are populated.
    outcome == ALREADY_CLAIMED:
        previous_completed says whether the prior attempt reached
        completion. caller_result and execution_result are None.
    """
    outcome: OrchestrationOutcome
    previous_completed: bool = False
    caller_result: Optional[CallerResult] = None
    execution_result: Optional[CommandExecutionResult] = None


def orchestrate_command(
    conversation_id: ConversationId,
    external_message_id: ExternalMessageId,
    message: str,
    observation: SignalObservation,
    dispatch_plan: DispatchPlan,
    engine: OrderEngine,
    session_store: InMemoryConversationSessionStore,
    idempotency_store: InMemoryIdempotencyStore,
    *,
    resolve_operation_fn: Callable = resolve_operation,
) -> OrchestrationResult:
    """
    Idempotent COMMAND processing for a single message identity.

    If the identity has already been claimed, no pipeline runs and no
    state is touched. Otherwise, the canonical path runs and state
    is saved.

    Exceptions raised by the canonical path propagate unchanged; the
    claim remains incomplete, honoring P77.
    """
    key = IdempotencyKey(
        conversation_id=conversation_id,
        external_message_id=external_message_id,
    )

    claim_status = idempotency_store.claim(key)
    if claim_status is ClaimStatus.ALREADY_CLAIMED:
        record = idempotency_store.get(key)
        return OrchestrationResult(
            outcome=OrchestrationOutcome.ALREADY_CLAIMED,
            previous_completed=bool(record and record.completed),
        )

    state: OrderState = session_store.get_or_create(conversation_id)

    caller_result = invoke(
        message,
        observation,
        dispatch_plan,
        state,
        resolve_operation_fn=resolve_operation_fn,
    )
    execution_result = compose_command_execution(
        caller_result, state, engine,
    )

    if execution_result.state is not None:
        session_store.save(conversation_id, execution_result.state)
    else:
        session_store.save(conversation_id, state)

    idempotency_store.complete(key)

    return OrchestrationResult(
        outcome=OrchestrationOutcome.PROCESSED,
        caller_result=caller_result,
        execution_result=execution_result,
    )