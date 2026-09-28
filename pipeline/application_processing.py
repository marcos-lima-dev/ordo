"""
ORDO — Application processing boundary.

Composes QUERY and COMMAND signals from a raw message into a
SignalObservation, then produces a DispatchPlan via the canonical
planner. It does NOT execute domain work, resolve identity, or own
state.

Pipeline:

    message
        -> QueryIntentProvider.predict
        -> CommandEvidenceProvider.predict
        -> SignalObservation(query=..., command=...)
        -> plan(observation)
        -> ProcessingResult(observation, dispatch_plan)

Principles honored:
    P78  CHANNEL IDENTITY != MESSAGE IDENTITY
    P79  CONVERSATION MAPPING DEPENDS ONLY ON CHANNEL IDENTITY
    P82  APPLICATION PROCESSING COMPOSES SIGNALS; IT DOES NOT EXECUTE DOMAIN WORK
    P83  SHADOW OBSERVES POTENTIAL DISPATCH WITHOUT EXERCISING APPLICATION AUTHORITY
    P84  SHADOW v1 ENDS AT THE DISPATCH PLAN

This module does NOT:
    - receive ConversationId, ExternalMessageId, or ChannelIdentity;
    - receive or mutate OrderState;
    - call application_caller, application_orchestrator, or command_execution;
    - acquire idempotency claims;
    - execute QUERY read-side;
    - touch OrderEngine;
    - know Telegram, WhatsApp, or any provider;
    - move or duplicate the CommandSafetyGuard.
"""
from __future__ import annotations

from dataclasses import dataclass

from pipeline.command_evidence_provider import CommandEvidenceProvider
from pipeline.dispatch_plan import DispatchPlan
from pipeline.dispatch_planner import plan
from pipeline.query_intent_provider import QueryIntentProvider
from pipeline.signal_observation import (
    CommandObservation,
    QueryObservation,
    SignalObservation,
)


@dataclass(frozen=True)
class ProcessingResult:
    """
    Output of the application processing boundary.

    observation:   the SignalObservation composed from providers.
    dispatch_plan: the DispatchPlan produced by plan(observation).

    No state, no identity, no execution.
    """
    observation: SignalObservation
    dispatch_plan: DispatchPlan


class ApplicationProcessor:
    """
    Composes signal observations and a dispatch plan from a raw
    message. Does nothing else.

    Dependencies are mandatory and injected. No default providers.
    """

    def __init__(
        self,
        query_provider: QueryIntentProvider,
        command_provider: CommandEvidenceProvider,
    ) -> None:
        self._query_provider = query_provider
        self._command_provider = command_provider

    def process(self, message: str) -> ProcessingResult:
        """
        Produce ProcessingResult for `message`.

        - calls the QUERY provider exactly once;
        - calls the COMMAND provider exactly once;
        - builds SignalObservation preserving both signals independently;
        - calls plan(observation) exactly once.

        Provider exceptions propagate unchanged.
        """
        query_signal = self._query_provider.predict(message)
        command_evidence = self._command_provider.predict(message)

        observation = SignalObservation(
            query=QueryObservation(signal=query_signal),
            command=CommandObservation(evidence=command_evidence),
        )
        dispatch_plan = plan(observation)

        return ProcessingResult(
            observation=observation,
            dispatch_plan=dispatch_plan,
        )