"""
ORDO — Conversation session (in-memory).

Minimal boundary that preserves OrderState across turns for a given
ConversationId. The store's only job is to hold state; it does not
interpret messages, resolve identity, or mutate commercial data.

Principles honored:
    P68  CONVERSATION IDENTITY != CHANNEL IDENTITY
    P69  CONVERSATION BOUNDARY RESOLVES IDENTITY; SESSION STORE OWNS STATE
    P70  SESSION STORE PRESERVES STATE; DOMAIN EXECUTION MUTATES COMMERCIAL STATE
    P71  MESSAGE IDENTITY != IDEMPOTENCY
    P72  CHANNEL INTEGRATION MUST NOT OWN ORDER LIFECYCLE

This module does NOT:
    - know Telegram, WhatsApp, or any provider-specific identifier;
    - mutate items, quantities, status, or any commercial field;
    - execute commands or call the OrderEngine;
    - deduplicate messages;
    - lock, version, or transact;
    - persist to disk or external storage.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from order.state import OrderState


@dataclass(frozen=True)
class ConversationId:
    """
    Opaque internal conversation identity.

    MUST NOT contain channel-specific semantics (telegram, whatsapp,
    phone numbers, chat ids). Channel adapters translate external
    identity into this value outside the core.
    """
    value: str


class InMemoryConversationSessionStore:
    """
    In-memory store of OrderState keyed by ConversationId.

    Contract:
        get_or_create(cid) -> OrderState
        save(cid, state)   -> None

    This is a minimal implementation to prove multi-turn state
    ownership. It is NOT production persistence.

    In-memory semantics:
        - get_or_create returns the SAME OrderState instance on
          subsequent calls for the same ConversationId.
        - save stores the given reference.

    Object identity is an implementation detail, NOT part of the
    contract. Future persistent implementations may copy, serialize,
    or reconstruct freely. Callers must treat the returned state as
    the source of truth for the current turn only.
    """

    def __init__(self) -> None:
        self._states: Dict[str, OrderState] = {}

    def get_or_create(self, conversation_id: ConversationId) -> OrderState:
        """
        Return the OrderState for `conversation_id`, creating an empty
        one on first access.
        """
        key = conversation_id.value
        if key not in self._states:
            self._states[key] = OrderState()
        return self._states[key]

    def save(
        self, conversation_id: ConversationId, state: OrderState,
    ) -> None:
        """
        Persist the given state for `conversation_id`.

        Future implementations may evolve this signature to accept an
        expected revision for optimistic concurrency. This Stage does
        not add such a parameter.
        """
        self._states[conversation_id.value] = state