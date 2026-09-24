"""
ORDO — ResolvedQuery contract (Track 10, Stage 2).

ResolvedQuery represents a query that has been semantically resolved
to a specific SKU, with a specific query_type.

Read-side type. Does NOT participate in the mutation pipeline. Does
NOT pass through the command engine. Does NOT touch OrderState.

Architectural separation (Track 10 T10-P2):

    ResolvedQuery    !=    ResolvedOperation
    query (read)     !=    command (write)

UNANSWERABLE is deliberately NOT part of this type. Whether the query
can be answered is a concern of the future read-side provider, not of
semantic resolution.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List


class QueryType(Enum):
    """
    Types of read-side queries supported by the ORDO contract.

    Independent from OperationType (Track 10 T10-P2).
    QUERY_PRICE and QUERY_AVAILABILITY are NOT added to OperationType.
    """
    QUERY_PRICE = "QUERY_PRICE"
    QUERY_AVAILABILITY = "QUERY_AVAILABILITY"


@dataclass
class ResolvedQuery:
    """
    A query semantically resolved to a SKU.

    Contract:
        query_type  — required; must be a valid QueryType
        product_id  — required for is_valid() == True
        evidence    — reserved for boundary-level provenance;
                      populated at the boundary's discretion, NOT
                      automatically propagated from
                      QueryResolutionResult.evidence.
    """
    query_type: QueryType
    product_id: Optional[str] = None
    evidence: List[str] = field(default_factory=list)

    def is_valid(self) -> bool:
        """
        A ResolvedQuery is valid iff it carries a resolved product_id.

        query_type is enforced by the dataclass constructor (no
        default), so it is always a valid QueryType here.
        """
        return self.product_id is not None