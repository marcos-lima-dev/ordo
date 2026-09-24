"""
ORDO — Semantic Intent Router (Track 10, Stage 4B).

Contract + deterministic routing layer that:

    1. Represents canonical semantic intent (SemanticIntent) independently
       of OperationType and QueryType.
    2. Categorizes intent into COMMAND | QUERY | UNKNOWN.
    3. Bridges COMMAND intents to OperationType (and only COMMAND).
    4. Bridges QUERY intents to QueryType (and only QUERY).

This module does NOT:
    - interpret natural language;
    - detect keywords;
    - apply fuzzy matching;
    - call any model or classifier;
    - import OrderEngine, OrderState, CatalogRetriever, ProductResolver,
      OperationResolver, ModularAdapter, or any ML library.

It defines the meaning of a semantic intent, once that intent is
provided by an authorized upstream source. Recognition of intent from
natural language remains the responsibility of a dedicated upstream
component (not this module).

Parsing from raw text is closed-set and exact:

    "QUERY_PRICE"        → SemanticIntent.QUERY_PRICE
    "quanto custa"       → SemanticIntent.UNKNOWN
    "PRICE"              → SemanticIntent.UNKNOWN
    None                 → SemanticIntent.UNKNOWN

No repair, no inference, no coercion.

Architectural invariants preserved:
    T10-P1  QUERY ≠ COMMAND
    T10-P2  ResolvedQuery ≠ ResolvedOperation
    T10-P4  ResolutionResult remains COMMAND-only
"""
from enum import Enum
from typing import Optional

from order.resolved_operation import OperationType
from order.resolved_query import QueryType


class SemanticIntent(Enum):
    """
    Canonical semantic intent values, mirroring the frozen
    semantic contract v1.1.2.

    This enum is intentionally independent from:
        - OperationType (COMMAND-only, Track 9C)
        - QueryType     (QUERY-only, Track 10 Stage 2)
    """
    ADD_ITEM = "ADD_ITEM"
    REMOVE_ITEM = "REMOVE_ITEM"
    CHANGE_QUANTITY = "CHANGE_QUANTITY"
    REPLACE_ITEM = "REPLACE_ITEM"
    QUERY_PRICE = "QUERY_PRICE"
    QUERY_AVAILABILITY = "QUERY_AVAILABILITY"
    CONFIRM_ORDER = "CONFIRM_ORDER"
    CANCEL_ORDER = "CANCEL_ORDER"
    UNKNOWN = "UNKNOWN"


class MessageCategory(Enum):
    """
    Top-level category of a message.

    COMMAND  — intent that alters or finalizes OrderState
    QUERY    — intent that requests information without altering OrderState
    UNKNOWN  — intent not recognized as either
    """
    COMMAND = "COMMAND"
    QUERY = "QUERY"
    UNKNOWN = "UNKNOWN"


# =============================================
# Domain categorization (deterministic, non-linguistic)
# =============================================
# Maps a canonical semantic intent to its category.
# UNKNOWN is explicitly mapped to MessageCategory.UNKNOWN — no fallback.

_CATEGORY_BY_INTENT = {
    SemanticIntent.ADD_ITEM: MessageCategory.COMMAND,
    SemanticIntent.REMOVE_ITEM: MessageCategory.COMMAND,
    SemanticIntent.CHANGE_QUANTITY: MessageCategory.COMMAND,
    SemanticIntent.REPLACE_ITEM: MessageCategory.COMMAND,
    SemanticIntent.CONFIRM_ORDER: MessageCategory.COMMAND,
    SemanticIntent.CANCEL_ORDER: MessageCategory.COMMAND,
    SemanticIntent.QUERY_PRICE: MessageCategory.QUERY,
    SemanticIntent.QUERY_AVAILABILITY: MessageCategory.QUERY,
    SemanticIntent.UNKNOWN: MessageCategory.UNKNOWN,
}


# =============================================
# COMMAND → OperationType bridge
# =============================================
# Only COMMAND semantic intents have an OperationType counterpart.
# QUERY and UNKNOWN must NOT appear here.

_OPERATION_TYPE_BY_COMMAND_INTENT = {
    SemanticIntent.ADD_ITEM: OperationType.ADD_ITEM,
    SemanticIntent.REMOVE_ITEM: OperationType.REMOVE_ITEM,
    SemanticIntent.CHANGE_QUANTITY: OperationType.CHANGE_QUANTITY,
    SemanticIntent.REPLACE_ITEM: OperationType.REPLACE_ITEM,
    SemanticIntent.CONFIRM_ORDER: OperationType.CONFIRM_ORDER,
    SemanticIntent.CANCEL_ORDER: OperationType.CANCEL_ORDER,
}


# =============================================
# QUERY → QueryType bridge
# =============================================
# Only QUERY semantic intents have a QueryType counterpart.
# COMMAND and UNKNOWN must NOT appear here.

_QUERY_TYPE_BY_QUERY_INTENT = {
    SemanticIntent.QUERY_PRICE: QueryType.QUERY_PRICE,
    SemanticIntent.QUERY_AVAILABILITY: QueryType.QUERY_AVAILABILITY,
}


# =============================================
# Public API
# =============================================

def parse_semantic_intent(raw) -> SemanticIntent:
    """
    Closed-set, exact parsing from a raw value to SemanticIntent.

    Accepts only:
        - a string whose exact value matches a SemanticIntent member.

    Returns SemanticIntent.UNKNOWN for:
        - any other string;
        - None;
        - any non-str value.

    No fuzzy matching, no keyword detection, no natural-language
    inference, no coercion.
    """
    if not isinstance(raw, str):
        return SemanticIntent.UNKNOWN
    try:
        return SemanticIntent(raw)
    except ValueError:
        return SemanticIntent.UNKNOWN


def categorize(intent: SemanticIntent) -> MessageCategory:
    """
    Deterministic categorization of a canonical semantic intent.

    UNKNOWN maps to MessageCategory.UNKNOWN — no fallback.
    Any value not in the closed map also returns UNKNOWN.
    """
    return _CATEGORY_BY_INTENT.get(intent, MessageCategory.UNKNOWN)


def to_operation_type(intent: SemanticIntent) -> Optional[OperationType]:
    """
    Bridge: SemanticIntent → OperationType.

    Only COMMAND semantic intents have a valid OperationType.
    QUERY and UNKNOWN return None.
    """
    return _OPERATION_TYPE_BY_COMMAND_INTENT.get(intent)


def to_query_type(intent: SemanticIntent) -> Optional[QueryType]:
    """
    Bridge: SemanticIntent → QueryType.

    Only QUERY semantic intents have a valid QueryType.
    COMMAND and UNKNOWN return None.
    """
    return _QUERY_TYPE_BY_QUERY_INTENT.get(intent)