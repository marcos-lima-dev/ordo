"""
PA-1 Authority Wrapper.

Applies PA-1 Policy Slice v0 at the resolution boundary without altering
CallerResult, ProcessingResult, OrderState, or resolve_operation's public
contract.

States:
    ABSENT                -> delegate to real_fn unchanged
    SINGLE + EXISTS       -> delegate with pre_resolved_product_id
    SINGLE + NOT_EXISTS   -> NEEDS_CLARIFICATION (IDENTIFIER_NOT_FOUND)
    SINGLE + UNVERIFIABLE -> NEEDS_CLARIFICATION (IDENTIFIER_UNVERIFIABLE)
    MULTIPLE              -> NEEDS_CLARIFICATION (MULTIPLE_IDENTIFIERS)

Composition principle: Safety dominates PA-1 Authority. This wrapper is
expected to sit inside the CommandSafetyGuard chain, never outside it.

REPLACE_ITEM scope note:
    pre_resolved_product_id is defined for ADD_ITEM only in v0. The
    semantics for REPLACE_ITEM (source vs replacement) are not yet
    decided; the kwarg is ignored by resolve_operation for other
    op_types. See integration report.

This module does NOT:
    - execute operations or mutate commercial state;
    - call into domain execution;
    - infer quantity or target;
    - correct or fuzzy-match identifiers.
"""
from __future__ import annotations

from typing import Callable, List

from order.resolution_result import ResolutionResult, OutcomeType

from pipeline.pa1_observer import observe, PA1Observation
from pipeline.pa1_verifier import (
    canonical_identifier,
    verify_all,
    EXISTS,
    NOT_EXISTS,
    UNVERIFIABLE,
)


_REASON_IDENTIFIER_NOT_FOUND = "IDENTIFIER_NOT_FOUND"
_REASON_IDENTIFIER_UNVERIFIABLE = "IDENTIFIER_UNVERIFIABLE"
_REASON_MULTIPLE_IDENTIFIERS = "MULTIPLE_IDENTIFIERS"


def _clarification(reason_code: str, raws: List[str]) -> ResolutionResult:
    return ResolutionResult(
        outcome=OutcomeType.NEEDS_CLARIFICATION,
        reason_code=reason_code,
        evidence=list(raws),
    )


def make_pa1_authority_wrapper(
    real_fn: Callable,
    *,
    observe_fn: Callable = observe,
    verify_fn: Callable = verify_all,
) -> Callable:
    """
    Return a resolve_operation-shaped callable that applies PA-1 Policy
    Slice v0 before delegating.

    The returned callable has signature:
        (message: str, state) -> ResolutionResult

    real_fn must accept the keyword-only argument
    ``pre_resolved_product_id`` (see resolution_pipeline.resolve_operation).
    """
    def wrapped(message: str, state) -> ResolutionResult:
        obs: PA1Observation = observe_fn(message)

        if obs.presence != "PRESENT":
            return real_fn(message, state)

        verifications = list(verify_fn([o.raw for o in obs.occurrences]))

        # MULTIPLE — conservative v0, no collapse.
        if len(obs.occurrences) > 1:
            return _clarification(
                _REASON_MULTIPLE_IDENTIFIERS,
                [o.raw for o in obs.occurrences],
            )

        # SINGLE
        raw = obs.occurrences[0].raw
        status = verifications[0].status

        if status == EXISTS:
            canonical = canonical_identifier(raw)
            return real_fn(
                message,
                state,
                pre_resolved_product_id=canonical,
            )

        if status == NOT_EXISTS:
            return _clarification(_REASON_IDENTIFIER_NOT_FOUND, [raw])

        if status == UNVERIFIABLE:
            return _clarification(_REASON_IDENTIFIER_UNVERIFIABLE, [raw])

        # Unknown status — fail conservative.
        return _clarification(_REASON_IDENTIFIER_UNVERIFIABLE, [raw])

    return wrapped