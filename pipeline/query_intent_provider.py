"""
ORDO — Query Intent Provider contract (Track 10, Stage 4F).

Defines the minimal substitutable interface for QUERY recognition.

Scope (Stage 4F):
    - QUERY recognition only.
    - COMMAND path is untouched.
    - REPLACE_ITEM remains in OperationResolver.

Principle (T10-P9):
    PROVIDER SIGNAL ≠ SEMANTIC INTENT

    The provider emits a query-domain signal. It does NOT emit
    SemanticIntent directly. Mapping signal→SemanticIntent (when
    applicable) is the caller's responsibility.

Principle (T10-P10):
    NOT_QUERY IS A POSITIVE NEGATIVE CLASSIFICATION.

    QueryIntentSignal.NOT_QUERY means the provider EVALUATED the
    message and CONCLUDED it does not belong to the recognized
    QUERY domain.

    NOT_QUERY does NOT mean:
        - provider uncertainty;
        - possible query with uncertain subtype;
        - low confidence;
        - operational failure;
        - generic fallback.

    A provider that cannot decide between PRICE and AVAILABILITY
    must not convert that uncertainty into NOT_QUERY. The policy
    for uncertainty is UNSPECIFIED / DEFERRED — no additional
    state is introduced in this contract.

Contract:
    - predict(message) -> QueryIntentSignal
    - Deterministic.
    - No product resolution, no catalog, no state.
    - Failure contract (from Stage 4D-D3):
        * evaluated  → QueryIntentSignal
        * operational failure → explicit exception

States:
    QUERY_PRICE         — evaluated as a price query
    QUERY_AVAILABILITY  — evaluated as an availability query
    NOT_QUERY           — evaluated and positively classified as
                          not belonging to the QUERY domain

Rejected states (for the minimum contract):
    UNKNOWN   — not necessary for the minimum demonstrated contract.
                Operational failure is an explicit exception, not a
                state. If a future gate demonstrates a real need for
                an additional semantic state, this contract may be
                revised.
    AMBIGUOUS — no demonstrated real case; subtype disambiguation,
                when needed, belongs downstream.

This module does NOT:
    - interpret intent from language (no heuristics, no models);
    - resolve product;
    - touch OrderState / OrderEngine;
    - import any adapter, model or ML library.
"""
from abc import ABC, abstractmethod
from enum import Enum


class QueryIntentSignal(Enum):
    """
    Output signal from a QueryIntentProvider.

    Independent from SemanticIntent (9-way) and from
    MessageCategory (COMMAND / QUERY / UNKNOWN).

    NOT_QUERY semantics (T10-P10):
        NOT_QUERY is a positive negative classification. It asserts
        that the provider evaluated the message and concluded it is
        not a recognized query. It is not a fallback for uncertainty,
        operational failure, or subtype indecision.
    """
    QUERY_PRICE = "QUERY_PRICE"
    QUERY_AVAILABILITY = "QUERY_AVAILABILITY"
    NOT_QUERY = "NOT_QUERY"


class QueryIntentProvider(ABC):
    """
    Contract for QUERY recognition.

    Implementations must be deterministic and must NOT:
        - resolve product;
        - retrieve catalog;
        - touch OrderState;
        - mutate anything.
    """

    @abstractmethod
    def predict(self, message: str) -> QueryIntentSignal:
        """
        Return a query-domain signal for `message`.

        Semantics:
            - evaluated as price query        → QueryIntentSignal.QUERY_PRICE
            - evaluated as availability query → QueryIntentSignal.QUERY_AVAILABILITY
            - evaluated, positively classified as not a query
                                              → QueryIntentSignal.NOT_QUERY
            - operational failure             → raise (never return a signal)

        Note (T10-P10):
            NOT_QUERY is a positive negative classification. It must
            not be used as a fallback for uncertainty, subtype
            indecision, or operational failure. A provider that
            cannot evaluate must raise.
        """
        raise NotImplementedError