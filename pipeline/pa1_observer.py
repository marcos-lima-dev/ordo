"""
PA-1 Observer — observe Explicit Identifier Input in a raw message.

P105: Evidence representation ≠ resolution authority.

This module ONLY observes. It does not:
  - verify existence;
  - correct values;
  - infer intent;
  - consult semantic resolution;
  - consult alias indexes;
  - consult any query transformation step.

Contract: PA1 Explicit Identifier Input Contract v0
Rule:     PA1 Acceptance Rule Design v0
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Tuple


_ACCEPTANCE_RULE_ID = "pa1_acceptance_rule_v0"

# Acceptance Rule v0 — only observed family.
#
#   prefix:    CQ (case-insensitive)
#   separator: optional hyphen or single whitespace
#   value:     exactly two decimal digits
#   boundary:  not followed by a word character (letter, digit, underscore)
#
# MUST accept: CQ-44, cq-44, CQ44, CQ 44, CQ-99
# MUST reject: 44, CQ, "aquele CQ que falamos", CQ44ok, CQ-999
#
# No expansion to _ . / or three-digit values in v0.
_PATTERN = re.compile(r"\b[Cc][Qq](?:[-\s])?(\d{2})(?!\w)")


@dataclass(frozen=True)
class PA1Occurrence:
    """One accepted observation of an Explicit Domain Identifier."""
    raw: str                     # exact substring, as written by the customer
    span: Tuple[int, int]        # (start, end) offsets in the raw message
    recognition_provenance: str  # which rule accepted this occurrence


@dataclass(frozen=True)
class PA1Observation:
    """The result of PA-1 observation over one raw message."""
    presence: str                              # "ABSENT" | "PRESENT"
    occurrences: Tuple[PA1Occurrence, ...]     # () when ABSENT
    message_length: int


def observe(raw_message: str) -> PA1Observation:
    """
    Apply the Acceptance Rule to a raw message.

    Returns PA-1 ABSENT if no occurrence is accepted.
    Returns PA-1 PRESENT with ALL accepted occurrences otherwise.

    Multiplicity is preserved. No collapsing, no choosing, no correction.
    """
    if not isinstance(raw_message, str) or raw_message == "":
        return PA1Observation(
            presence="ABSENT",
            occurrences=(),
            message_length=len(raw_message) if isinstance(raw_message, str) else 0,
        )

    occurrences = tuple(
        PA1Occurrence(
            raw=match.group(0),
            span=(match.start(0), match.end(0)),
            recognition_provenance=_ACCEPTANCE_RULE_ID,
        )
        for match in _PATTERN.finditer(raw_message)
    )

    if not occurrences:
        return PA1Observation(
            presence="ABSENT",
            occurrences=(),
            message_length=len(raw_message),
        )

    return PA1Observation(
        presence="PRESENT",
        occurrences=occurrences,
        message_length=len(raw_message),
    )