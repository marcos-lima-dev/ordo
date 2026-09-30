"""
PA-1 Verifier — factually verify whether an accepted identifier corresponds
to an active product identity in the authoritative source.

P105: Evidence representation ≠ resolution authority.

Verification is a factual lookup. It does not:
  - consult semantic retrieval;
  - consult aliases;
  - consult semantic resolution components;
  - correct, suggest, or infer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from order.catalog_retriever import CatalogRetriever


EXISTS = "EXISTS"
NOT_EXISTS = "NOT_EXISTS"
UNVERIFIABLE = "UNVERIFIABLE"


@dataclass(frozen=True)
class PA1Verification:
    occurrence_raw: str
    status: str   # EXISTS | NOT_EXISTS | UNVERIFIABLE


def _lookup_key(raw: str) -> str:
    """
    Produce the canonical lookup key for an accepted occurrence.

    This is a REPRESENTATION-level operation, not a value correction.
    The Observer preserves raw verbatim. This function only builds the
    key used to query the authoritative source.

    Accepted forms (per Acceptance Rule v0):
        CQ-44  -> CQ-44
        cq-44  -> CQ-44
        CQ44   -> CQ-44
        CQ 44  -> CQ-44
    """
    s = raw.strip().upper()
    # Strip the accepted separators.
    for sep in ("-", " ", "\t"):
        s = s.replace(sep, "")
    # Canonical shape: CQ + 2 digits
    if len(s) == 4 and s.startswith("CQ") and s[2:].isdigit():
        return f"CQ-{s[2:]}"
    return s


def verify(
    occurrence_raw: str,
    catalog: Optional[CatalogRetriever] = None,
) -> PA1Verification:
    """
    Verify an accepted occurrence against the authoritative active-product
    identity source.

    Returns EXISTS, NOT_EXISTS, or UNVERIFIABLE.

    Does not consult semantic retrieval, aliases, or semantic resolution.
    """
    if catalog is None:
        try:
            catalog = CatalogRetriever()
        except Exception:
            return PA1Verification(occurrence_raw=occurrence_raw, status=UNVERIFIABLE)

    key = _lookup_key(occurrence_raw)

    try:
        products = getattr(catalog, "catalog", None)
        if products is None:
            return PA1Verification(occurrence_raw=occurrence_raw, status=UNVERIFIABLE)
        for product in products:
            if isinstance(product, dict) and product.get("product_id") == key:
                return PA1Verification(occurrence_raw=occurrence_raw, status=EXISTS)
    except Exception:
        return PA1Verification(occurrence_raw=occurrence_raw, status=UNVERIFIABLE)

    return PA1Verification(occurrence_raw=occurrence_raw, status=NOT_EXISTS)


def verify_all(
    occurrences_raw: List[str],
    catalog: Optional[CatalogRetriever] = None,
) -> List[PA1Verification]:
    """Verify each accepted occurrence independently. Multiplicity preserved."""
    if catalog is None:
        try:
            catalog = CatalogRetriever()
        except Exception:
            catalog = None
    return [verify(raw, catalog=catalog) for raw in occurrences_raw]