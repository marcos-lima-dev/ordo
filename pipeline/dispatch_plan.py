"""
ORDO — Dispatch Plan contract (Track 10, Stage 4I.5).

Pure data types for representing coordination decisions derived
from a SignalObservation.

Scope:
    - Data only. No planning logic. No policy. No pipeline calls.
    - No observations stored.
    - No domain invocation data stored.
    - No execution authorization.

Principles honored:
    T10-P22  COORDINATION != EXECUTION
    T10-P24  DISPATCH TARGET != PIPELINE FUNCTION
    T10-P29  OBSERVATION != PLAN STORAGE
    T10-P30  DISPATCH PLAN IS NEVER EXECUTION AUTHORIZATION
    T10-P38  DOMAIN ABSENCE IS EXPLICIT PLAN STATE
    T10-P39  COORDINATION DECISION != DOMAIN INVOCATION DATA
    T10-P40  INFORMATION LOSS MUST PRESERVE AN AUTHORITATIVE SOURCE

This module does NOT:
    - plan or coordinate anything;
    - import SignalObservation;
    - import any provider, recognizer, adapter, or pipeline;
    - carry SemanticIntent, OperationType, QueryType, or CommandLabel;
    - carry payload, priority, ordering, or execution semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Tuple


class DispatchTarget(Enum):
    """
    Coordination domain of a dispatch decision.

    Represents a domain, not a Python function (T10-P24).
    """
    QUERY = "QUERY"
    COMMAND = "COMMAND"


class DispatchAction(Enum):
    """
    Coordination action for a domain.

    These are states of coordination, not outcomes of execution.
    DISPATCH means: the domain pipeline is eligible to be invoked.
    It does NOT authorize execution (T10-P22 / T10-P30).
    """
    DISPATCH = "DISPATCH"
    NO_DISPATCH_UNRESOLVED = "NO_DISPATCH_UNRESOLVED"
    NO_DISPATCH_NOT_QUERY = "NO_DISPATCH_NOT_QUERY"
    NO_DISPATCH_ABSENT = "NO_DISPATCH_ABSENT"
    NO_DISPATCH_INDETERMINATE = "NO_DISPATCH_INDETERMINATE"
    NO_DISPATCH_NO_OBSERVATION = "NO_DISPATCH_NO_OBSERVATION"


@dataclass(frozen=True)
class DispatchDecision:
    """
    A single coordination decision for one domain.

    Carries only:
        - target: DispatchTarget (domain);
        - action: DispatchAction (state of coordination).

    Does NOT carry payload, observation, semantic intent, or any
    pipeline reference (T10-P39).
    """
    target: DispatchTarget
    action: DispatchAction


_DOMAINS = (DispatchTarget.QUERY, DispatchTarget.COMMAND)


@dataclass(frozen=True)
class DispatchPlan:
    """
    A coordination plan.

    Cardinality invariant (T10-P38):
        Every valid DispatchPlan contains exactly one decision per
        domain. For the current domains {QUERY, COMMAND}, this means
        exactly two decisions: one QUERY, one COMMAND.

    Tuple physical order has NO contractual semantics. It does not
    represent priority, precedence, or execution ordering.

    The plan is not execution authorization (T10-P30).
    """
    decisions: Tuple[DispatchDecision, ...]

    def __post_init__(self) -> None:
        decisions = self.decisions
        if not isinstance(decisions, tuple):
            raise TypeError(
                f"decisions must be a tuple, got {type(decisions).__name__}"
            )
        for d in decisions:
            if not isinstance(d, DispatchDecision):
                raise TypeError(
                    f"decisions must contain DispatchDecision, "
                    f"got {type(d).__name__}"
                )

        targets = [d.target for d in decisions]
        counts = {t: targets.count(t) for t in set(targets)}

        # Every defined domain must appear exactly once.
        for domain in _DOMAINS:
            if counts.get(domain, 0) != 1:
                raise ValueError(
                    f"DispatchPlan must contain exactly one decision "
                    f"for domain {domain.value}; found "
                    f"{counts.get(domain, 0)}"
                )

        # No extra domains beyond the defined ones.
        for target in counts:
            if target not in _DOMAINS:
                raise ValueError(
                    f"DispatchPlan contains unknown domain: {target!r}"
                )

        # Total count must equal the number of defined domains.
        if len(decisions) != len(_DOMAINS):
            raise ValueError(
                f"DispatchPlan must contain exactly {len(_DOMAINS)} "
                f"decisions (one per domain); found {len(decisions)}"
            )
