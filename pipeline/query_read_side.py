"""
ORDO — Canonical QUERY read-side composition (Track 10, Stage 4J.4).

Composes three existing pieces:

    CallerResult.query (QueryResolutionResult | None)
        -> to_resolved_query()
        -> ResolvedQuery | None
        -> retrieve_fact()
        -> FactRetrievalResult

Preserves three distinct states:

    NOT_INVOKED   -- no query was invoked by the application caller
    NOT_RESOLVED  -- query invoked, to_resolved_query returned None
    RETRIEVED     -- ResolvedQuery produced, retrieve_fact invoked

Principles honored:
    T10-P6   RESOLVED QUERY != ANSWERED QUERY
    T10-P49  FACT RETRIEVAL STATUS DESCRIBES THE FACT RETRIEVAL OUTCOME
    T10-P53  QUERY RESOLUTION FAILURE PRECEDES FACT RETRIEVAL
    T10-P54  READ-SIDE COMPOSITION DOES NOT CHANGE DOMAIN SEMANTICS
    T10-P55  FACT RETRIEVAL REQUIRES A RESOLVED QUERY

This module does NOT:
    - recognize language;
    - resolve product;
    - reclassify status;
    - consult the catalog;
    - mutate OrderState;
    - touch the command path;
    - render a response;
    - invent fallback.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from order.fact_read_side import retrieve_fact
from order.fact_retrieval_result import FactRetrievalResult
from order.query_boundary import to_resolved_query
from order.query_resolution_result import QueryResolutionResult
from order.resolved_query import ResolvedQuery

from pipeline.application_caller import CallerResult


class QueryReadSideStatus(Enum):
    NOT_INVOKED = "NOT_INVOKED"
    NOT_RESOLVED = "NOT_RESOLVED"
    RETRIEVED = "RETRIEVED"


@dataclass(frozen=True)
class QueryReadSideResult:
    status: QueryReadSideStatus
    query_resolution: Optional[QueryResolutionResult] = None
    resolved_query: Optional[ResolvedQuery] = None
    fact_retrieval: Optional[FactRetrievalResult] = None


def compose_query_read_side(
    caller_result: CallerResult,
    *,
    to_resolved_query_fn: Callable = to_resolved_query,
    retrieve_fact_fn: Callable = retrieve_fact,
) -> QueryReadSideResult:
    """
    Compose the QUERY read-side chain from a CallerResult.

    Only reads ``caller_result.query``. The ``command`` field is not
    inspected, not modified, and not propagated.
    """
    qr = caller_result.query
    if qr is None:
        return QueryReadSideResult(
            status=QueryReadSideStatus.NOT_INVOKED,
        )

    rq = to_resolved_query_fn(qr)
    if rq is None:
        return QueryReadSideResult(
            status=QueryReadSideStatus.NOT_RESOLVED,
            query_resolution=qr,
        )

    fr = retrieve_fact_fn(rq)
    return QueryReadSideResult(
        status=QueryReadSideStatus.RETRIEVED,
        query_resolution=qr,
        resolved_query=rq,
        fact_retrieval=fr,
    )