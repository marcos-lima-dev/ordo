"""
ORDO — QueryResolutionResult contract (Track 10, Stage 2).

Pre-boundary result of resolving a query intent.

Mirrors the shape of ResolutionResult (COMMAND side) but is a
distinct type (Track 10 T10-P4):

    ResolutionResult        — COMMAND side (frozen by Track 9C)
    QueryResolutionResult   — QUERY side (this module)

OutcomeType is deliberately NOT extended with QUERY (T10-P4).
QueryResolutionStatus is a distinct enum.

This type does NOT:
    - touch OrderState
    - import or invoke the command engine
    - pass through the command boundary
    - mutate EXECUTION_REQUIREMENTS

BLOCKED is deliberately NOT included. For COMMAND, BLOCKED covers
"pending_resolution blocks execution". Queries do not interact with
OrderState; a malformed or incomplete query is represented by
NEEDS_CLARIFICATION with an appropriate reason_code.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List

from order.resolved_query import QueryType


class QueryResolutionStatus(Enum):
    RESOLVED = "RESOLVED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    PRODUCT_NOT_FOUND = "PRODUCT_NOT_FOUND"


@dataclass
class QueryResolutionResult:
    """
    Result of resolving a query intent, before any read-side boundary.

    Contract:
        status      — required; one of QueryResolutionStatus
        query_type  — required; must be a valid QueryType
        product_id  — set only when status == RESOLVED
        reason_code — optional; populated for non-RESOLVED outcomes
        evidence    — provenance of the resolution; not automatically
                      propagated to ResolvedQuery at the boundary.
    """
    status: QueryResolutionStatus
    query_type: QueryType
    product_id: Optional[str] = None
    reason_code: Optional[str] = None
    evidence: List[str] = field(default_factory=list)