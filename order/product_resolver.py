from typing import List, Optional, Dict


class ResolutionStatus:
    EXACT_MATCH = "EXACT_MATCH"
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_FOUND = "NOT_FOUND"


class ProductResolver:
    """
    Decide status de resolução com base em candidatos + evidência.

    Regra formal (9B.2):
      retrieval evidence != execution authorization evidence.

    Só autorizam EXACT_MATCH:
      ALIAS_EXACT, NAME_EXACT, ORIGINAL_EXACT,
      APPROVED_ALIAS, ENTITY_SIGNAL.

    NÃO autorizam EXACT_MATCH por si sós:
      ALIAS_TOKEN, NAME_TOKEN, ALIAS_SUBSET, NAME_SUBSET, *_FUZZY.

    evidence=None NÃO autoriza EXACT_MATCH.
    """

    POSITIVE_EVIDENCE_SOURCES = {
        "ALIAS_EXACT",
        "NAME_EXACT",
        "ORIGINAL_EXACT",
        "APPROVED_ALIAS",
        "ENTITY_SIGNAL",
    }

    def resolve(
        self,
        candidates: List[str],
        product_term: Optional[str] = None,
        brand: Optional[str] = None,
        evidence: Optional[Dict[str, str]] = None,
    ) -> str:
        if not candidates:
            return ResolutionStatus.NOT_FOUND

        if len(candidates) == 1:
            cid = candidates[0]

            # evidence=None NÃO autoriza EXACT_MATCH
            if evidence is None:
                return ResolutionStatus.AMBIGUOUS

            source = evidence.get(cid, "")
            is_positive = any(
                src in source for src in self.POSITIVE_EVIDENCE_SOURCES
            )
            if not is_positive:
                return ResolutionStatus.AMBIGUOUS

            return ResolutionStatus.EXACT_MATCH

        return ResolutionStatus.AMBIGUOUS

    def is_resolved(self, status: str) -> bool:
        return status in [ResolutionStatus.EXACT_MATCH, ResolutionStatus.HIGH_CONFIDENCE]