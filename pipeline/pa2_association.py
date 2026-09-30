"""
PA-2 Validated Historical Association — Stage 1.

Represents and retrieves validated historical associations by
observable reference, without interpretation, normalization,
product-resolution authority, or command-execution authority.

This module does NOT:
    - interpret the current message;
    - normalize expressions;
    - apply association to any current message;
    - resolve product identity;
    - grant authority;
    - execute commands.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from threading import Lock
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class HistoricalAssociationRecord:
    """
    One validated historical association.

    expression:                literal, as originally clarified.
                               Never normalized, never derived.
    product_id:                CQ-XX identity resolved at clarification.
    clarification_provenance:  evidence of the clarification that
                               validated this association. Preserved
                               as provided; not authenticated by the
                               store.
    """
    expression: str
    product_id: str
    clarification_provenance: str

    def __post_init__(self) -> None:
        if not isinstance(self.expression, str) or not self.expression:
            raise ValueError("expression must be a non-empty string")
        if not isinstance(self.product_id, str) or not self.product_id:
            raise ValueError("product_id must be a non-empty string")
        if (
            not isinstance(self.clarification_provenance, str)
            or not self.clarification_provenance
        ):
            raise ValueError(
                "clarification_provenance must be a non-empty string"
            )


class PA2AssociationStore(ABC):
    """
    Factual store of validated historical associations, keyed by an
    opaque observable reference.

    lookup returns ALL records under the reference. It does not
    interpret any message, does not filter, does not normalize, does
    not select. Zero/one/multiple preserved. Provenance preserved.
    """

    @abstractmethod
    def lookup(
        self, reference: Any
    ) -> Tuple[HistoricalAssociationRecord, ...]:
        ...


class InMemoryPA2AssociationStore(PA2AssociationStore):
    """
    Minimal in-memory implementation.

    Simple list keyed by reference. Does not assume atomicity,
    lifecycle, persistence, or identity semantics beyond what is
    required here.

    This is not production persistence.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._records: Dict[Any, List[HistoricalAssociationRecord]] = {}

    def add(
        self, reference: Any, record: HistoricalAssociationRecord,
    ) -> None:
        """Append a validated association under `reference`."""
        with self._lock:
            self._records.setdefault(reference, []).append(record)

    def lookup(
        self, reference: Any
    ) -> Tuple[HistoricalAssociationRecord, ...]:
        """Return all records under `reference`, in insertion order."""
        with self._lock:
            return tuple(self._records.get(reference, []))