"""
ORDO — Application domain caller (Track 10, Stage 4J.2).

Stateless application-layer component that reads a DispatchPlan and
invokes the appropriate domain pipeline for each DISPATCH decision,
returning a domain-separated CallerResult.

Principles honored:
    T10-P22  COORDINATION != EXECUTION
    T10-P41  QUERY invocation data has an authoritative source
    T10-P42  QUERY signal translation is mechanical
    T10-P43  Dispatch authorizes invocation, not the observation alone
    T10-P44  Non-dispatchable query signal is a contract violation
    T10-P45  Application caller invokes; it does not resolve or execute
    T10-P46  Domain invocation results remain domain-separated
    T10-P47  Cross-contract inconsistency fails at the consumption boundary
    T10-P48  Application caller does not own conversation state

This module does NOT:
    - recognize, plan, or coordinate;
    - resolve QUERY or COMMAND by itself;
    - execute operations or mutate OrderState;
    - own conversation state (state is a parameter);
    - repair, reinterpret, or skip incoherent inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from order.query_resolution_result import QueryResolutionResult
from order.resolution_result import ResolutionResult
from order.state import OrderState

from pipeline.dispatch_plan import (
    DispatchAction,
    DispatchPlan,
    DispatchTarget,
)
from pipeline.query_intent_provider import QueryIntentSignal
from pipeline.query_resolution_pipeline import resolve_query
from pipeline.query_signal_translation import query_signal_to_semantic_intent
from pipeline.resolution_pipeline import resolve_operation
from pipeline.signal_observation import (
    CommandEvidence,
    SignalObservation,
)


_DISPATCHABLE_QUERY_SIGNALS = frozenset({
    QueryIntentSignal.QUERY_PRICE,
    QueryIntentSignal.QUERY_AVAILABILITY,
})


class DomainInvocationInconsistency(Exception):
    """
    Raised when DispatchPlan and SignalObservation are incoherent at
    the caller boundary (T10-P47).

    The caller does NOT repair, reinterpret, or skip silently.
    """

    def __init__(self, target: DispatchTarget, reason: str) -> None:
        self.target = target
        self.reason = reason
        super().__init__(
            f"incoherent {target.value} dispatch: {reason}"
        )


@dataclass(frozen=True)
class CallerResult:
    """
    Result of a single application-caller invocation (T10-P46).

    query:   QueryResolutionResult if the QUERY pipeline was invoked.
    command: ResolutionResult if the COMMAND pipeline was invoked.

    None means "domain not invoked". It does NOT mean negative
    resolution, error, or blockage.
    """
    query: Optional[QueryResolutionResult]
    command: Optional[ResolutionResult]


def _validate_query_coherence(observation: SignalObservation) -> None:
    q = observation.query
    if q is None:
        raise DomainInvocationInconsistency(
            DispatchTarget.QUERY, "no query observation"
        )
    if q.signal not in _DISPATCHABLE_QUERY_SIGNALS:
        raise DomainInvocationInconsistency(
            DispatchTarget.QUERY,
            f"non-dispatchable signal: {q.signal.name}",
        )


def _validate_command_coherence(observation: SignalObservation) -> None:
    c = observation.command
    if c is None:
        raise DomainInvocationInconsistency(
            DispatchTarget.COMMAND, "no command observation"
        )
    if c.evidence is not CommandEvidence.PRESENT:
        raise DomainInvocationInconsistency(
            DispatchTarget.COMMAND,
            f"non-dispatchable evidence: {c.evidence.name}",
        )


def invoke(
    message: str,
    observation: SignalObservation,
    dispatch_plan: DispatchPlan,
    state: OrderState,
    *,
    resolve_query_fn: Callable = resolve_query,
    resolve_operation_fn: Callable = resolve_operation,
) -> CallerResult:
    """
    Read the DispatchPlan; for each domain whose decision is
    DISPATCH, validate coherence with the SignalObservation, then
    invoke the corresponding pipeline.

    Returns a CallerResult with domain results explicitly separated
    (T10-P46).

    Coherence is validated for all dispatched domains before any
    pipeline is invoked (T10-P47).
    """
    by_target = {d.target: d.action for d in dispatch_plan.decisions}
    query_dispatch = (
        by_target[DispatchTarget.QUERY] is DispatchAction.DISPATCH
    )
    command_dispatch = (
        by_target[DispatchTarget.COMMAND] is DispatchAction.DISPATCH
    )

    # Validate coherence for all dispatched domains first.
    if query_dispatch:
        _validate_query_coherence(observation)
    if command_dispatch:
        _validate_command_coherence(observation)

    query_result: Optional[QueryResolutionResult] = None
    command_result: Optional[ResolutionResult] = None

    if query_dispatch:
        semantic_intent = query_signal_to_semantic_intent(
            observation.query.signal
        )
        query_result = resolve_query_fn(message, semantic_intent)

    if command_dispatch:
        command_result = resolve_operation_fn(message, state)

    return CallerResult(query=query_result, command=command_result)