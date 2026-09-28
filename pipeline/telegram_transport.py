"""
ORDO — Telegram transport (long polling, Shadow Pilot v1).

Responsibility: obtain raw updates from the official Telegram Bot API.
No interpretation, no ORDO semantics.

Principles honored:
    P86  CHANNEL TRANSPORT != CHANNEL ADAPTER

This module does NOT:
    - parse ORDO semantics;
    - recognize intent;
    - know ChannelIdentity, ExternalMessageId, or the adapter;
    - expose the bot token outside its own instance;
    - log the token anywhere.

The transport is intentionally small and replaceable. Swapping long
polling for webhook later must not require touching the adapter.
"""
from __future__ import annotations

import json
from typing import Callable, Dict, List, Optional
from urllib.parse import urlencode
from urllib.request import urlopen


class TransportFailure(Exception):
    """Raised for HTTP/network failures in the transport layer."""


_HttpGetter = Callable[[str, float], bytes]


def _default_http_get(url: str, timeout: float) -> bytes:
    with urlopen(url, timeout=timeout) as response:  # noqa: S310
        return response.read()


class TelegramTransport:
    """
    Long-polling transport for the official Telegram Bot API.

    The bot token is held internally and used only to build the request
    URL. It is never returned, logged, or exposed by this class.
    """

    _BASE = "https://api.telegram.org"

    def __init__(
        self,
        token: str,
        *,
        http_get: Optional[_HttpGetter] = None,
        timeout: float = 30.0,
    ) -> None:
        if not isinstance(token, str) or not token.strip():
            raise ValueError("token must be a non-empty string")
        self._token = token
        self._http_get = http_get or _default_http_get
        self._timeout = timeout

    def get_updates(
        self,
        *,
        offset: Optional[int] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """
        Fetch a batch of raw updates.

        `offset` follows Telegram Bot API semantics: the first
        update_id to be returned. Updates with a lower update_id are
        considered confirmed and will not be returned again. Callers
        should set offset to `last_update_id + 1` from the previous
        batch.
        """
        params = {"limit": limit}
        if offset is not None:
            params["offset"] = offset

        url = (
            f"{self._BASE}/bot{self._token}/getUpdates?"
            f"{urlencode(params)}"
        )

        try:
            body = self._http_get(url, self._timeout)
        except Exception as exc:
            raise TransportFailure(str(exc)) from exc

        try:
            payload = json.loads(body)
        except Exception as exc:
            raise TransportFailure(
                "invalid JSON from Telegram"
            ) from exc

        if not isinstance(payload, dict) or payload.get("ok") is not True:
            raise TransportFailure("Telegram API returned ok=false")

        result = payload.get("result")
        if not isinstance(result, list):
            raise TransportFailure("Telegram API returned no result list")

        return result


def next_offset(updates: List[Dict]) -> Optional[int]:
    """
    Compute the next `offset` from a batch, per Telegram Bot API
    semantics. Returns None if there is no progress to make.
    """
    update_ids = [
        u.get("update_id") for u in updates
        if isinstance(u, dict) and isinstance(u.get("update_id"), int)
    ]
    if not update_ids:
        return None
    return max(update_ids) + 1