"""
ORDO — Telegram adapter (Shadow Pilot v1).

Translates a raw Telegram update into ORDO contracts:

    ChannelIdentity("telegram", str(chat.id))
    ExternalMessageId(str(message.message_id))
    text: str

Or classifies the update as IGNORED / REJECTED.

Principles honored:
    P78  CHANNEL IDENTITY != MESSAGE IDENTITY
    P85  TRANSPORT EVENT IDENTITY != MESSAGE IDENTITY
    P86  CHANNEL TRANSPORT != CHANNEL ADAPTER

This module does NOT:
    - call HTTP / Telegram API (that is the transport);
    - recognize intent;
    - build SignalObservation or DispatchPlan;
    - decide SHADOW or EXECUTION;
    - touch OrderState, OrderEngine, idempotency;
    - retain usernames, names, profile, media, or the raw payload.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from pipeline.channel_identity import ChannelIdentity
from pipeline.idempotency import ExternalMessageId


class ParseStatus(Enum):
    PARSED = "PARSED"
    IGNORED = "IGNORED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class ParsedMessage:
    channel_identity: ChannelIdentity
    external_message_id: ExternalMessageId
    text: str


@dataclass(frozen=True)
class ParseResult:
    status: ParseStatus
    reason: str
    message: Optional[ParsedMessage] = None


_IGNORED_REASONS = frozenset({
    "no_message",
    "from_bot",
    "edited_message",
    "channel_post",
})


class TelegramAdapter:
    """
    Pure translator: raw Telegram update -> ORDO contracts or a
    rejection/ignored classification.

    Config:
        allowed_chat_ids: iterable of int or str chat ids permitted to
        reach the pipeline. Empty means no chat is allowed.

    The adapter never inspects chat.type beyond requiring "private",
    and never reads usernames, names, profile, or the raw payload
    beyond what is strictly required.
    """

    def __init__(self, allowed_chat_ids) -> None:
        self._allowed = {str(c) for c in allowed_chat_ids}

    def parse(self, update: dict) -> ParseResult:
        if not isinstance(update, dict):
            return ParseResult(ParseStatus.REJECTED, "malformed_update")

        if "edited_message" in update:
            return ParseResult(ParseStatus.IGNORED, "edited_message")
        if "channel_post" in update:
            return ParseResult(ParseStatus.IGNORED, "channel_post")

        message = update.get("message")
        if not isinstance(message, dict):
            return ParseResult(ParseStatus.IGNORED, "no_message")

        sender = message.get("from")
        if isinstance(sender, dict) and sender.get("is_bot") is True:
            return ParseResult(ParseStatus.IGNORED, "from_bot")

        chat = message.get("chat")
        if not isinstance(chat, dict):
            return ParseResult(ParseStatus.REJECTED, "malformed_identity")

        if chat.get("type") != "private":
            return ParseResult(ParseStatus.REJECTED, "not_private_chat")

        chat_id = chat.get("id")
        if chat_id is None:
            return ParseResult(ParseStatus.REJECTED, "malformed_identity")

        if str(chat_id) not in self._allowed:
            return ParseResult(ParseStatus.REJECTED, "chat_not_allowed")

        message_id = message.get("message_id")
        if message_id is None:
            return ParseResult(ParseStatus.REJECTED, "malformed_identity")

        text = message.get("text")
        if not isinstance(text, str) or not text.strip():
            return ParseResult(ParseStatus.REJECTED, "no_text")

        parsed = ParsedMessage(
            channel_identity=ChannelIdentity(
                channel="telegram",
                external_conversation_id=str(chat_id),
            ),
            external_message_id=ExternalMessageId(value=str(message_id)),
            text=text,
        )
        return ParseResult(ParseStatus.PARSED, "parsed", parsed)