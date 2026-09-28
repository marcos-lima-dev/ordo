"""
ORDO — Telegram Shadow runner (v1).

Wires:
    raw update
        -> TelegramAdapter
        -> ChannelIdentity -> ConversationId (identity state)
        -> ApplicationProcessor
        -> ObservationRecord
        -> STOP.

Principles honored:
    P82  APPLICATION PROCESSING COMPOSES SIGNALS; DOES NOT EXECUTE DOMAIN WORK
    P83  SHADOW OBSERVES POTENTIAL DISPATCH WITHOUT EXERCISING APPLICATION AUTHORITY
    P84  SHADOW v1 ENDS AT THE DISPATCH PLAN
    P87  SHADOW IDENTITY STATE != COMMERCIAL STATE
    P88  SHADOW OBSERVATION MUST NOT CONSUME EXECUTION IDEMPOTENCY

This module does NOT:
    - call application_caller, application_orchestrator, or command_execution;
    - touch OrderEngine, OrderState, or the ConversationSessionStore;
    - acquire idempotency claims;
    - perform outbound / sendMessage;
    - retain the token, the raw payload, or user profile metadata.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional

from pipeline.application_processing import (
    ApplicationProcessor,
    ProcessingResult,
)
from pipeline.conversation_mapping import InMemoryConversationMappingStore
from pipeline.conversation_session import ConversationId
from pipeline.telegram_adapter import (
    ParseStatus,
    TelegramAdapter,
)
from pipeline.telegram_transport import (
    TelegramTransport,
    next_offset,
)


@dataclass(frozen=True)
class ObservationRecord:
    """
    Shadow observation record for one parsed message.

    Minimum fields per Design Gate. No provider payload, no profile
    metadata, no token, no update_id in the record.
    """
    conversation_id: ConversationId
    external_message_id: str
    text: str
    observation: object  # SignalObservation
    dispatch_plan: object  # DispatchPlan
    observed_at: float


def process_update(
    update: dict,
    adapter: TelegramAdapter,
    mapping: InMemoryConversationMappingStore,
    processor: ApplicationProcessor,
) -> Optional[ObservationRecord]:
    """
    Parse one update and, if parsed, produce an ObservationRecord.

    IGNORED and REJECTED updates return None. The token is never
    involved at this layer. No commercial state, no idempotency
    claim, no outbound action.
    """
    result = adapter.parse(update)
    if result.status is not ParseStatus.PARSED:
        return None

    parsed = result.message
    conversation_id = mapping.get_or_create(parsed.channel_identity)
    processing: ProcessingResult = processor.process(parsed.text)

    return ObservationRecord(
        conversation_id=conversation_id,
        external_message_id=parsed.external_message_id.value,
        text=parsed.text,
        observation=processing.observation,
        dispatch_plan=processing.dispatch_plan,
        observed_at=time.time(),
    )


def run_shadow_cycle(
    transport: TelegramTransport,
    adapter: TelegramAdapter,
    mapping: InMemoryConversationMappingStore,
    processor: ApplicationProcessor,
    *,
    offset: Optional[int] = None,
    limit: int = 100,
) -> tuple[List[ObservationRecord], Optional[int]]:
    """
    Run one polling cycle. Returns (records, next_offset).

    The caller is responsible for threading the next_offset back into
    the following cycle. The transport holds the token; this function
    never sees it.
    """
    updates = transport.get_updates(offset=offset, limit=limit)
    records: List[ObservationRecord] = []
    for update in updates:
        record = process_update(update, adapter, mapping, processor)
        if record is not None:
            records.append(record)
    return records, next_offset(updates)