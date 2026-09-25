"""
ORDO — FactRetrievalResult contract (Track 10).

Read-side result of attempting to retrieve a business fact for a
ResolvedQuery.

Three and only three states (T10-P49):

    FACT_FOUND          -- authoritative source exists and provided the fact
    FACT_NOT_FOUND      -- authoritative source exists but has no fact
                           for this query/product
    SOURCE_UNAVAILABLE  -- no authoritative source exists for this fact type

SOURCE_UNAVAILABLE != FACT_NOT_FOUND (T10-P50).

Today the repository has no authoritative source for PRICE or
AVAILABILITY. Therefore this module only ever produces
SOURCE_UNAVAILABLE. FACT_FOUND and FACT_NOT_FOUND are reserved
semantically and will be produced only when a real source and its
contract exist (T10-P52).

No business payload is defined here. No currency, no price, no
quantity_on_hand, no freshness. Those types are born only with an
authoritative source contract.
"""
from dataclasses import dataclass
from enum import Enum

from order.resolved_query import ResolvedQuery


class FactRetrievalStatus(Enum):
    FACT_FOUND = "FACT_FOUND"
    FACT_NOT_FOUND = "FACT_NOT_FOUND"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"


@dataclass(frozen=True)
class FactRetrievalResult:
    query: ResolvedQuery
    status: FactRetrievalStatus