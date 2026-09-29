from typing import List, Optional, Dict

from order.evidence import Evidence


class ResolutionStatus:
    EXACT_MATCH = "EXACT_MATCH"
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_FOUND = "NOT_FOUND"


# Positive-for-identity-resolution policy, applied over Evidence facts.
# Reproduces the legacy substring classification
#   any(src in provenance_str for src in POSITIVE_EVIDENCE_SOURCES)
# for every provenance string currently produced by CatalogRetriever.
#
# Equivalence: for legacy string "{stream}_{kind}_{strength}",
#   "ALIAS_EXACT"  in s  ⇔  kind == "ALIAS"  and strength == "EXACT"
#   "NAME_EXACT"   in s  ⇔  kind == "NAME"   and strength == "EXACT"
#   "ORIGINAL_EXACT" in s ⇔ kind == "ORIGINAL_NAME" and strength == "EXACT"
# APPROVED_ALIAS / ENTITY_SIGNAL have no producers; not modeled in v0.
_POSITIVE_MATCH_STRENGTH = "EXACT"
_POSITIVE_MATCH_KINDS = frozenset({"ALIAS", "NAME", "ORIGINAL_NAME"})


class ProductResolver:
    """
    Decide status de resolução com base em candidatos + evidência.

    P105: representation of evidence is distinct from authority to resolve.
    Positivity is a policy decision applied over observable facts.
    Under the current policy (unchanged from 9B.2), an Evidence is positive
    for product identity resolution when:
        match_strength == "EXACT"
        and match_kind in {"ALIAS", "NAME", "ORIGINAL_NAME"}.
    """

    @staticmethod
    def _is_positive(ev: Evidence) -> bool:
        return (
            ev.match_strength == _POSITIVE_MATCH_STRENGTH
            and ev.match_kind in _POSITIVE_MATCH_KINDS
        )

    def resolve(
        self,
        candidates: List[str],
        product_term: Optional[str] = None,
        brand: Optional[str] = None,
        evidence: Optional[Dict[str, List[Evidence]]] = None,
    ) -> str:
        if not candidates:
            return ResolutionStatus.NOT_FOUND

        if len(candidates) == 1:
            cid = candidates[0]

            if evidence is None:
                return ResolutionStatus.AMBIGUOUS

            ev_list = evidence.get(cid, []) or []
            if not any(self._is_positive(ev) for ev in ev_list):
                return ResolutionStatus.AMBIGUOUS

            return ResolutionStatus.EXACT_MATCH

        return ResolutionStatus.AMBIGUOUS

    def is_resolved(self, status: str) -> bool:
        return status in [
            ResolutionStatus.EXACT_MATCH,
            ResolutionStatus.HIGH_CONFIDENCE,
        ]