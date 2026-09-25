"""
ORDO — Query signal translation (Track 10, Stage 4J.1).

Pure, deterministic translation from a dispatchable QueryIntentSignal
to a SemanticIntent, for use by the future application caller when
the DispatchPlan says QUERY -> DISPATCH.

Mapping (frozen):

    QUERY_PRICE        -> SemanticIntent.QUERY_PRICE
    QUERY_AVAILABILITY -> SemanticIntent.QUERY_AVAILABILITY

Non-dispatchable signals (UNRESOLVED, NOT_QUERY) are a contract
violation at this boundary and fail explicitly (T10-P44).

Principles honored:
    T10-P41  QUERY INVOCATION DATA HAS AN AUTHORITATIVE SOURCE
    T10-P42  QUERY SIGNAL TRANSLATION IS MECHANICAL, NOT SEMANTIC RESOLUTION
    T10-P44  NON-DISPATCHABLE QUERY SIGNAL IS A CONTRACT VIOLATION

This module does NOT:
    - parse messages;
    - plan, coordinate, or dispatch;
    - touch DispatchPlan, SignalObservation, or OrderState;
    - consult any catalog or pipeline;
    - resolve or execute anything.
"""
from __future__ import annotations

from pipeline.query_intent_provider import QueryIntentSignal
from pipeline.semantic_intent_router import SemanticIntent


class NonDispatchableQuerySignal(Exception):
    """
    Raised when the translation is called with a QueryIntentSignal
    that is not dispatchable (UNRESOLVED or NOT_QUERY).

    This is a contract violation at this boundary (T10-P44), not a
    normal outcome of translation.
    """

    def __init__(self, signal: QueryIntentSignal) -> None:
        self.signal = signal
        super().__init__(
            f"non-dispatchable QueryIntentSignal: {signal.name}"
        )


_DISPATCHABLE = {
    QueryIntentSignal.QUERY_PRICE: SemanticIntent.QUERY_PRICE,
    QueryIntentSignal.QUERY_AVAILABILITY: SemanticIntent.QUERY_AVAILABILITY,
}


def query_signal_to_semantic_intent(
    signal: QueryIntentSignal,
) -> SemanticIntent:
    """
    Translate a dispatchable QueryIntentSignal into a SemanticIntent.

    Raises NonDispatchableQuerySignal for UNRESOLVED, NOT_QUERY, or
    any signal outside the dispatchable domain.
    """
    try:
        return _DISPATCHABLE[signal]
    except KeyError:
        raise NonDispatchableQuerySignal(signal) from None