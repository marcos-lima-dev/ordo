"""
ORDO — Query Intent Provider contract (Track 10, Stage 4F / 4F.1).

Defines the minimal substitutable interface for QUERY recognition.

Scope (Stage 4F / 4F.1):
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

Principle (T10-P11):
    ABSENCE OF QUERY EVIDENCE ≠ NOT_QUERY.

    Lack of sufficient QUERY evidence does not authorize a
    NOT_QUERY classification. When the provider evaluated the
    message but cannot safely produce QUERY_PRICE,
    QUERY_AVAILABILITY, or NOT_QUERY, the correct semantic
    outcome is UNRESOLVED.

Principle (T10-P12):
    UNRESOLVED ≠ PROVIDER FAILURE.

    UNRESOLVED is a valid semantic outcome. Operational failure
    remains an explicit exception, never a signal.

Principle (T10-P13):
    UNRESOLVED ≠ NOT_QUERY.

    NOT_QUERY is a positive classification of non-query.
    UNRESOLVED is the absence of a safe classification.

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
    UNRESOLVED          — evaluated, but insufficient evidence to
                          safely produce QUERY_PRICE,
                          QUERY_AVAILABILITY, or NOT_QUERY

Rejected states (for the minimum contract):
    UNKNOWN   — not necessary for the minimum demonstrated contract.
                Operational failure is an explicit exception, not a
                state.
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

    UNRESOLVED semantics (T10-P12 / T10-P13):
        UNRESOLVED is a valid semantic outcome. It asserts that the
        provider evaluated the message but lacks sufficient evidence
        to safely produce QUERY_PRICE, QUERY_AVAILABILITY, or
        NOT_QUERY. It is not a provider failure and it is not
        equivalent to NOT_QUERY.
    """
    QUERY_PRICE = "QUERY_PRICE"
    QUERY_AVAILABILITY = "QUERY_AVAILABILITY"
    NOT_QUERY = "NOT_QUERY"
    UNRESOLVED = "UNRESOLVED"


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
            - evaluated, insufficient evidence to safely classify
                                              → QueryIntentSignal.UNRESOLVED
            - operational failure             → raise (never return a signal)

        Note (T10-P10):
            NOT_QUERY is a positive negative classification. It must
            not be used as a fallback for uncertainty, subtype
            indecision, or operational failure. A provider that
            cannot evaluate must raise.

        Note (T10-P12 / T10-P13):
            UNRESOLVED is a valid semantic outcome, not a provider
            failure, and not equivalent to NOT_QUERY. A provider
            that evaluated the message but lacks sufficient evidence
            to safely classify it must return UNRESOLVED rather than
            NOT_QUERY or an exception.
        """
        raise NotImplementedError
