"""
ORDO — Conversation mapping store.

Maps ChannelIdentity -> ConversationId. Separate responsibility from
the session store (P80): mapping resolves WHO, session preserves
STATE.

Principles honored:
    P68  CONVERSATION IDENTITY != CHANNEL IDENTITY
    P69  CONVERSATION BOUNDARY RESOLVES IDENTITY; SESSION STORE OWNS STATE
    P79  CONVERSATION MAPPING DEPENDS ONLY ON CHANNEL IDENTITY
    P80  CONVERSATION MAPPING != CONVERSATION STATE
    P81  CONVERSATION MAPPING CREATION IS ATOMIC BY CONTRACT

This module does NOT:
    - know Telegram, WhatsApp, or any provider;
    - store OrderState;
    - interpret messages;
    - deduplicate messages;
    - persist across processes.
"""
from __future__ import annotations

from threading import Lock
from typing import Dict, Optional
from uuid import uuid4

from pipeline.channel_identity import ChannelIdentity
from pipeline.conversation_session import ConversationId


class InMemoryConversationMappingStore:
    """
    In-memory mapping ChannelIdentity -> ConversationId.

    Atomicity of get_or_create is a CONTRACT (P81). The implementation
    uses a per-process lock so that concurrent calls for the same
    ChannelIdentity always observe the same ConversationId.

    A ChannelIdentity has at most one active ConversationId within
    this mapping.

    Not production persistence. Exists to prove the boundary and
    enable local E2E tests.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._mapping: Dict[ChannelIdentity, ConversationId] = {}

    def get_or_create(self, identity: ChannelIdentity) -> ConversationId:
        """
        Return the ConversationId for `identity`, creating one on
        first access.

        Atomic: two concurrent calls for the same ChannelIdentity
        return the same ConversationId.
        """
        with self._lock:
            existing = self._mapping.get(identity)
            if existing is not None:
                return existing
            new_id = ConversationId(value=uuid4().hex)
            self._mapping[identity] = new_id
            return new_id

    def get(self, identity: ChannelIdentity) -> Optional[ConversationId]:
        """Diagnostic lookup. Returns None for unknown identities."""
        with self._lock:
            return self._mapping.get(identity)