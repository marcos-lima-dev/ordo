"""
ORDO — Signal Observation types (Track 10, Stage 4I.1).

Pure data types for representing independent semantic observations
of a single message, before any coordination decision.

These types preserve independent QUERY and COMMAND observations
without collapsing them into a single semantic classification
(T10-P16, T10-P17, T10-P23).

Scope:
    - No recognition. No resolution. No dispatch. No execution.
    - No access to OrderState, OrderEngine, or any resolver.
    - No knowledge of OperationType, SemanticIntent, or QueryType.
    - No COMMAND intent value is carried (T10-P26).

Principles honored:
    T10-P16  SINGLE SIGNAL OUTPUT != SINGLE INTENT ASSUMPTION
    T10-P23  PRESERVE INDEPENDENT SIGNALS BEFORE COLLAPSE
    T10-P26  COMMAND EVIDENCE != COMMAND INTENT
    T10-P29  OBSERVATION != PLAN STORAGE
    T10-P30  DISPATCH PLAN IS NEVER EXECUTION AUTHORIZATION

This module does NOT:
    - interpret natural language;
    - call any provider or adapter;
    - import benchmark, order, or pipeline resolvers;
    - carry a COMMAND intent or operation type;
    - carry dispatch, routing, or execution semantics.

These types are the input to future observation/planning stages.
They are NOT the plan itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from pipeline.query_intent_provider import QueryIntentSignal


class CommandEvidence(Enum):
    """
    Evidence presence for the COMMAND domain.

    PRESENT:
        There is sufficient evidence to offer the message to the
        COMMAND pipeline. Does NOT say which operation exists
        (T10-P26).

    ABSENT:
        Positive evidence that the message does NOT belong to the
        COMMAND domain. Emitted only when a provider possesses such
        positive evidence (T10-P28).

    INDETERMINATE:
        The provider did not conclude presence or absence. This is
        the mapping for an "UNKNOWN" recognizer output (T10-P27).
        It is NOT equivalent to ABSENT.

    Operational failure of any provider is an exception, never a
    value of this enum.
    """
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    INDETERMINATE = "INDETERMINATE"


@dataclass(frozen=True)
class CommandObservation:
    """
    Observation of the COMMAND domain for a single message.

    Carries ONLY evidence presence. Does NOT carry a concrete
    COMMAND intent, operation type, or any resolved field.
    """
    evidence: CommandEvidence


@dataclass(frozen=True)
class QueryObservation:
    """
    Observation of the QUERY domain for a single message.

    Carries the QueryIntentSignal produced by a QueryIntentProvider.
    Preserves UNRESOLVED and NOT_QUERY as first-class values.
    """
    signal: QueryIntentSignal


@dataclass(frozen=True)
class SignalObservation:
    """
    Independent observations for a single message.

    Both fields are optional. Any combination is valid, including
    both absent. No global semantic classification of the message
    is asserted here (T10-P16 / T10-P17).
    """
    query: Optional[QueryObservation] = None
    command: Optional[CommandObservation] = None