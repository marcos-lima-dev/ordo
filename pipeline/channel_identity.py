"""
ORDO — Channel identity contract.

Represents a stable external origin for a conversation, as provided
by a channel adapter. Deliberately separate from ExternalMessageId
(P78) and from any internal ConversationId (P68).

Principles honored:
    P68  CONVERSATION IDENTITY != CHANNEL IDENTITY
    P72  CHANNEL INTEGRATION MUST NOT OWN ORDER LIFECYCLE
    P78  CHANNEL IDENTITY != MESSAGE IDENTITY
    P79  CONVERSATION MAPPING DEPENDS ONLY ON CHANNEL IDENTITY

This module does NOT:
    - know Telegram, WhatsApp, or any specific provider;
    - define a closed enum of channels;
    - carry message identity;
    - carry conversation state;
    - decide anything about processing.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChannelIdentity:
    """
    Stable external origin of a conversation.

    channel:                 free-form identifier provided by the
                             adapter (e.g. "telegram", "whatsapp",
                             "web", "discord"). Not a closed enum.
    external_conversation_id: provider-scoped identifier for the
                             conversation (chat id, phone number, ...).
                             Opaque to the core.

    A new message does NOT create a new ChannelIdentity (P78).
    """
    channel: str
    external_conversation_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.channel, str) or not self.channel.strip():
            raise ValueError("channel must be a non-empty string")
        if (
            not isinstance(self.external_conversation_id, str)
            or not self.external_conversation_id.strip()
        ):
            raise ValueError(
                "external_conversation_id must be a non-empty string"
            )