"""
ORDO — Pure Dispatch Planner (Track 10, Stage 4I.6).

Pure transformation:

    SignalObservation -> DispatchPlan

Coordinates already-observed signals. Does NOT recognize language,
does NOT resolve domain, does NOT execute anything.

Principles honored:
    T10-P22  COORDINATION != EXECUTION
    T10-P23  PRESERVE INDEPENDENT SIGNALS BEFORE COLLAPSE
    T10-P25  Sibling signals are never suppressed
    T10-P38  DOMAIN ABSENCE IS EXPLICIT PLAN STATE
    T10-P39  COORDINATION DECISION != DOMAIN INVOCATION DATA

Mapping (frozen for this Stage):

    QUERY:
        QUERY_PRICE        -> DISPATCH
        QUERY_AVAILABILITY -> DISPATCH
        UNRESOLVED         -> NO_DISPATCH_UNRESOLVED
        NOT_QUERY          -> NO_DISPATCH_NOT_QUERY
        absent             -> NO_DISPATCH_NO_OBSERVATION

    COMMAND:
        PRESENT            -> DISPATCH
        INDETERMINATE      -> NO_DISPATCH_INDETERMINATE
        ABSENT             -> NO_DISPATCH_ABSENT
        absent             -> NO_DISPATCH_NO_OBSERVATION

QUERY and COMMAND are evaluated independently. No winner, no
priority, no precedence, no sibling suppression.

This module does NOT:
    - resolve QUERY or COMMAND;
    - call any pipeline;
    - import OrderState, OrderEngine, or any resolver;
    - carry payload, priority, or ordering.
"""
from __future__ import annotations

from typing import Optional

from pipeline.dispatch_plan import (
    DispatchAction,
    DispatchDecision,
    DispatchPlan,
    DispatchTarget,
)
from pipeline.query_intent_provider import QueryIntentSignal
from pipeline.signal_observation import (
    CommandEvidence,
    CommandObservation,
    QueryObservation,
    SignalObservation,
)


_QUERY_ACTION = {
    QueryIntentSignal.QUERY_PRICE: DispatchAction.DISPATCH,
    QueryIntentSignal.QUERY_AVAILABILITY: DispatchAction.DISPATCH,
    QueryIntentSignal.UNRESOLVED: DispatchAction.NO_DISPATCH_UNRESOLVED,
    QueryIntentSignal.NOT_QUERY: DispatchAction.NO_DISPATCH_NOT_QUERY,
}

_COMMAND_ACTION = {
    CommandEvidence.PRESENT: DispatchAction.DISPATCH,
    CommandEvidence.INDETERMINATE: DispatchAction.NO_DISPATCH_INDETERMINATE,
    CommandEvidence.ABSENT: DispatchAction.NO_DISPATCH_ABSENT,
}


def _query_action(observation: Optional[QueryObservation]) -> DispatchAction:
    if observation is None:
        return DispatchAction.NO_DISPATCH_NO_OBSERVATION
    return _QUERY_ACTION[observation.signal]


def _command_action(observation: Optional[CommandObservation]) -> DispatchAction:
    if observation is None:
        return DispatchAction.NO_DISPATCH_NO_OBSERVATION
    return _COMMAND_ACTION[observation.evidence]


def plan(observation: SignalObservation) -> DispatchPlan:
    """
    Transform a SignalObservation into a DispatchPlan.

    Every plan contains exactly one decision per domain (T10-P38).
    QUERY and COMMAND are evaluated independently (no sibling
    suppression, no priority).

    The physical order of decisions in the returned tuple carries
    no contractual meaning.
    """
    query_decision = DispatchDecision(
        target=DispatchTarget.QUERY,
        action=_query_action(observation.query),
    )
    command_decision = DispatchDecision(
        target=DispatchTarget.COMMAND,
        action=_command_action(observation.command),
    )
    return DispatchPlan(decisions=(query_decision, command_decision))