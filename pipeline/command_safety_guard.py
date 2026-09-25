"""
ORDO — Command safety guard (multi-item safety gate, R4).

Detects representational overflow in a COMMAND message: the message
contains more independent commercial units (products, targets,
operations) than the singular COMMAND contract can safely represent.

Rule (R4):
    overflow  <=>  product_count > 1
                OR operation_count > 1
                OR some product entity contains an internal
                   structural separator

Quantity count is deliberately NOT part of R4 (empirical evidence:
introduces false positives without new true positives).

Principles honored:
    P59  REPRESENTATIONAL OVERFLOW MUST FAIL CLOSED
    P60  MULTIPLICITY MUST BE DETECTED BEFORE LOSSY COLLAPSE
    P61  SAFE GUARD != MULTI-OPERATION RESOLUTION
    P62  SAFETY EVIDENCE != SEMANTIC RESOLUTION
    P63  FALSE NEGATIVE DOMINATES FALSE POSITIVE
    P64  COMPOUND ENTITY IS SAFETY EVIDENCE, NOT MODEL INTENT
    P65  REPRESENTATIONAL_OVERFLOW BLOCKS COMMAND EXECUTION BEFORE
         SINGULAR RESOLUTION
    P66  SAFETY GUARD FAILURE MUST FAIL CLOSED
    P67  SAFETY EVIDENCE IS DIAGNOSTIC, NOT COMMERCIAL DATA

This module does NOT:
    - resolve product, quantity, or operation;
    - split messages;
    - produce multiple ResolutionResults;
    - associate product with quantity;
    - choose OperationType or target;
    - import any adapter or resolver;
    - execute anything.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Tuple

from order.resolution_result import OutcomeType, ResolutionResult


REASON_CODE_OVERFLOW = "REPRESENTATIONAL_OVERFLOW"

_ENTITY_LABELS = ("produto", "marca", "apresentacao")
_PRODUCT_LABEL = "produto"

_COMMAND_VERB_PATTERNS = (
    r"\bmanda\b", r"\btira\b", r"\bremove\b", r"\badiciona\b",
    r"\bcoloca\b", r"\bbota\b", r"\bquero\b", r"\bgostaria\b",
    r"\bcancela\b", r"\btroca\b", r"\bmuda\b", r"\bretira\b",
)

_INTERNAL_SEPARATORS = (" e ", ",", " mais ", " também ", " tambem ")


class GuardDecision(Enum):
    SAFE = "SAFE"
    REPRESENTATIONAL_OVERFLOW = "REPRESENTATIONAL_OVERFLOW"


@dataclass(frozen=True)
class SafetyResult:
    decision: GuardDecision
    evidence: Tuple[str, ...] = ()


class SafetyGuardFailure(Exception):
    """
    Raised when the guard cannot decide (extractor failure, etc.).

    Per P66, callers must fail closed: treat as block, never SAFE.
    """


class CommandSafetyGuard:
    """
    Detector of representational overflow for COMMAND messages.
    """

    def __init__(self, extractor, *, threshold: float = 0.3):
        # extractor: callable(message, labels, *, threshold) -> list[dict]
        self._extractor = extractor
        self._threshold = threshold

    def check(self, message: str) -> SafetyResult:
        try:
            entities = list(
                self._extractor(
                    message, _ENTITY_LABELS, threshold=self._threshold,
                )
            )
        except Exception as exc:
            raise SafetyGuardFailure(str(exc)) from exc

        products = [e for e in entities if e.get("label") == _PRODUCT_LABEL]
        product_count = len(products)
        operation_count = _count_verbs(message)

        evidence = []
        if product_count > 1:
            evidence.append(f"products:{product_count}")
        if operation_count > 1:
            evidence.append(f"operations:{operation_count}")
        for entity in products:
            if _has_internal_separator(entity.get("text", "")):
                start = entity.get("start")
                end = entity.get("end")
                evidence.append(f"compound_entity:{start}-{end}")
                break

        if evidence:
            return SafetyResult(
                decision=GuardDecision.REPRESENTATIONAL_OVERFLOW,
                evidence=tuple(evidence),
            )
        return SafetyResult(decision=GuardDecision.SAFE)


def _count_verbs(message: str) -> int:
    low = message.lower()
    return sum(
        len(re.findall(pattern, low)) for pattern in _COMMAND_VERB_PATTERNS
    )


def _has_internal_separator(text: str) -> bool:
    low = text.lower()
    return any(sep in low for sep in _INTERNAL_SEPARATORS)


def make_guarded_resolve_operation(guard: CommandSafetyGuard, real_fn):
    """
    Produce a `resolve_operation`-shaped callable guarded by `guard`.

    SAFE                      -> delegate to real_fn unchanged.
    REPRESENTATIONAL_OVERFLOW -> short-circuit with NEEDS_CLARIFICATION,
                                 reason_code=REPRESENTATIONAL_OVERFLOW.
    Guard failure (P66)       -> fail closed (same NEEDS_CLARIFICATION
                                 shape with evidence=("guard_failure",)).

    The returned callable is safe to pass as ``resolve_operation_fn``
    to ``application_caller.invoke``.
    """
    def guarded(message: str, state) -> ResolutionResult:
        try:
            result = guard.check(message)
        except SafetyGuardFailure:
            return _overflow_result(("guard_failure",))
        if result.decision is GuardDecision.REPRESENTATIONAL_OVERFLOW:
            return _overflow_result(result.evidence)
        return real_fn(message, state)
    return guarded


def _overflow_result(evidence: Tuple[str, ...]) -> ResolutionResult:
    return ResolutionResult(
        outcome=OutcomeType.NEEDS_CLARIFICATION,
        reason_code=REASON_CODE_OVERFLOW,
        evidence=list(evidence),
    )