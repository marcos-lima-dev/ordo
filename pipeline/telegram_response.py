"""
ORDO — Response composition for Telegram.

Minimal representation of a communicable response derived from an
execution outcome. This module does NOT execute domain work, does NOT
call Telegram, does NOT consult the catalog, does NOT resolve products,
does NOT reinterpret ambiguity, does NOT transform evidence into
authority, and does NOT create missing information.

Principle:
    Communication describes the result; it does not create a new result.

    Response Composition ≠ Response Delivery.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CommunicableResponse:
    """Minimal representation of a response to be delivered."""
    destination: str
    text: str


_OUTCOME_TEXT = {
    "EXECUTED":            "Pedido processado.",
    "CLARIFICATION":       "Preciso de mais informações para continuar.",
    "SAFETY_BLOCKED":      "Solicitação bloqueada por segurança.",
    "EXECUTION_DISABLED":  "Execução desabilitada no momento.",
    "DUPLICATE":           "Mensagem já recebida anteriormente.",
    "ERROR":               "Não foi possível processar sua mensagem.",
}


def compose_response(
    outcome_name: str,
    *,
    destination: Optional[str],
) -> Optional[CommunicableResponse]:
    """
    Map an execution outcome name to a communicable response.

    Returns None when no response should be sent:
      - destination is None (no chat to reply to);
      - outcome is NOT_ELIGIBLE (allowlist boundary);
      - outcome is unknown.

    Not eligible for processing ≠ eligible for response.
    """
    if destination is None:
        return None
    text = _OUTCOME_TEXT.get(outcome_name)
    if text is None:
        return None
    return CommunicableResponse(destination=destination, text=text)