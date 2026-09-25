"""
ORDO — Fact read-side boundary (Track 10).

Translates a ResolvedQuery into a FactRetrievalResult.

Current behavior:
    For any valid ResolvedQuery, returns SOURCE_UNAVAILABLE.

Reason:
    No authoritative source for PRICE or AVAILABILITY exists in the
    repository (see Track 10 business source audit). This is not a
    placeholder. This is the honest current answer.

This module does NOT:
    - re-resolve the product;
    - consult the catalog;
    - mutate OrderState;
    - call OrderEngine;
    - render a response;
    - invent price, currency, freshness, or stock.

Contract violations (T10-P51):
    A ResolvedQuery whose query_type is not a QueryType instance
    fails explicitly. Not a commercial state.
"""
from order.fact_retrieval_result import (
    FactRetrievalResult,
    FactRetrievalStatus,
)
from order.resolved_query import QueryType, ResolvedQuery


class InvalidResolvedQueryType(Exception):
    """ResolvedQuery with a query_type outside the QueryType domain."""

    def __init__(self, value):
        self.value = value
        super().__init__(f"invalid ResolvedQuery.query_type: {value!r}")


def retrieve_fact(query: ResolvedQuery) -> FactRetrievalResult:
    """
    Attempt to retrieve a business fact for `query`.

    Today there is no authoritative source, so this returns
    SOURCE_UNAVAILABLE for any valid query. When a source exists,
    this function is revisited.
    """
    if not isinstance(query.query_type, QueryType):
        raise InvalidResolvedQueryType(query.query_type)

    return FactRetrievalResult(
        query=query,
        status=FactRetrievalStatus.SOURCE_UNAVAILABLE,
    )