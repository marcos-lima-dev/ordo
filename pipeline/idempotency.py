"""
ORDO — Idempotency boundary (message identity).

Atomic claim + completion tracking for message identity. Lives at the
application layer; keeps OrderEngine ignorant of delivery concerns.

Principles honored:
    P71  MESSAGE IDENTITY != IDEMPOTENCY
    P75  IDEMPOTENCY CLAIM IS ATOMIC BY CONTRACT, NOT BY IMPLEMENTATION ACCIDENT
    P76  CLAIMED != COMPLETED
    P77  UNCERTAIN EXECUTION MUST NOT BE SILENTLY REPLAYED OR REPORTED AS COMPLETED

This module does NOT:
    - know Telegram, WhatsApp, or any provider-specific identifier;
    - interpret message content;
    - hash text, timestamps, or message content as identity;
    - touch OrderState, OrderEngine, or any resolver;
    - retry, recover, lease, or reconcile.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from threading import Lock
from typing import Dict, Optional

from pipeline.conversation_session import ConversationId


@dataclass(frozen=True)
class ExternalMessageId:
    """
    Opaque external message identity, provided by the channel adapter.

    MUST NOT be interpreted by the core/application layer. No
    Telegram/WhatsApp semantics. No encoding assumptions.
    """
    value: str


@dataclass(frozen=True)
class IdempotencyKey:
    """
    Logical idempotency key: (ConversationId, ExternalMessageId).

    Same text + different ExternalMessageId = distinct messages.
    Same ExternalMessageId + different ConversationId = distinct keys.
    """
    conversation_id: ConversationId
    external_message_id: ExternalMessageId


class ClaimStatus(Enum):
    CLAIMED = "CLAIMED"
    ALREADY_CLAIMED = "ALREADY_CLAIMED"


@dataclass(frozen=True)
class ClaimRecord:
    """
    Diagnostic view of a claim.

    claimed:   the identity was claimed by some caller.
    completed: that caller reached the defined completion point.
    """
    key: IdempotencyKey
    claimed: bool
    completed: bool


class InMemoryIdempotencyStore:
    """
    In-memory idempotency store.

    Atomicity is a CONTRACT (P75), not a runtime accident. The
    implementation uses a per-process lock so that `claim(key)` is
    atomically exclusive: exactly one caller receives CLAIMED for a
    given key, regardless of concurrency.

    This is NOT distributed. Multi-process idempotency is out of scope.

    This implementation is NOT production persistence. It exists to
    prove the contract and enable retry-safety tests.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._records: Dict[IdempotencyKey, Dict[str, bool]] = {}

    def claim(self, key: IdempotencyKey) -> ClaimStatus:
        """
        Atomically claim `key`.

        Returns CLAIMED if this caller acquired the exclusive right
        to process the identity. Returns ALREADY_CLAIMED otherwise,
        whether the previous attempt completed or not.
        """
        with self._lock:
            existing = self._records.get(key)
            if existing is not None and existing["claimed"]:
                return ClaimStatus.ALREADY_CLAIMED
            self._records[key] = {"claimed": True, "completed": False}
            return ClaimStatus.CLAIMED

    def complete(self, key: IdempotencyKey) -> None:
        """
        Mark `key` as completed.

        Raises KeyError if the key was never claimed. Calling
        `complete` twice is a no-op.
        """
        with self._lock:
            existing = self._records.get(key)
            if existing is None or not existing["claimed"]:
                raise KeyError(
                    f"cannot complete unclaimed idempotency key: {key!r}"
                )
            existing["completed"] = True

    def get(self, key: IdempotencyKey) -> Optional[ClaimRecord]:
        """Diagnostic lookup. Returns None for unknown keys."""
        with self._lock:
            existing = self._records.get(key)
            if existing is None:
                return None
            return ClaimRecord(
                key=key,
                claimed=existing["claimed"],
                completed=existing["completed"],
            )