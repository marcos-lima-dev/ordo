from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum
import copy
import re

from order.state import OrderState
from order.pending import PendingResolution


class PendingStatus(Enum):
    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INCOMPATIBLE = "INCOMPATIBLE"


@dataclass
class PendingResult:
    status: PendingStatus
    resolved_product_id: Optional[str] = None
    resolved_product_name: Optional[str] = None
    updated_pending: Optional[PendingResolution] = None
    evidence: List[str] = field(default_factory=list)
    reason_code: Optional[str] = None


class PendingResolver:
    """
    Resolve referências complementares contra uma pending_resolution existente.

    Uma mensagem só é absorvida pela pending se houver evidência de compatibilidade.
    Caso contrário, o fluxo normal de interpretação deve continuar.
    """

    NEW_OPERATION_VERBS = [
        "quero", "manda", "coloca", "bota", "gostaria", "preciso",
        "me ve", "me vê", "adiciona", "inclui", "põe", "poe",
    ]

    def resolve(
        self,
        message: str,
        state: OrderState,
        semantic_signals: dict,
        catalog_retriever,
    ) -> PendingResult:
        # 1. Sem pendência?
        if state.pending_resolution is None:
            return PendingResult(
                status=PendingStatus.NOT_APPLICABLE,
                evidence=["no_pending_resolution"],
            )

        pending = state.pending_resolution

        # 2. A mensagem parece complementar a pendência?
        if not self._is_complement_candidate(message, pending, semantic_signals):
            return PendingResult(
                status=PendingStatus.NOT_APPLICABLE,
                evidence=["not_a_complement_candidate"],
            )

        # 3. Extrair constraints
        constraints = self._extract_constraints(semantic_signals)
        if not constraints:
            return PendingResult(
                status=PendingStatus.NOT_APPLICABLE,
                evidence=["no_constraints_extracted"],
            )

        # 4. Aplicar constraints à pendência
        updated_pending = self._apply_constraints(pending, constraints)

        # 5. Tentar resolver com CatalogRetriever
        candidates = catalog_retriever.retrieve_with_constraints(
            updated_pending.product_term or "",
            brand=updated_pending.brand,
            presentation=updated_pending.presentation,
        )

        evidence = [f"constraint_{k}" for k in constraints.keys()]

        if len(candidates) == 1:
            return PendingResult(
                status=PendingStatus.RESOLVED,
                resolved_product_id=candidates[0],
                updated_pending=updated_pending,
                evidence=evidence + ["single_candidate"],
            )

        if len(candidates) > 1:
            return PendingResult(
                status=PendingStatus.AMBIGUOUS,
                updated_pending=updated_pending,
                evidence=evidence + [f"{len(candidates)}_candidates"],
                reason_code="AMBIGUOUS_PRODUCT",
            )

        return PendingResult(
            status=PendingStatus.INCOMPATIBLE,
            evidence=evidence + ["no_candidates"],
            reason_code="INCOMPATIBLE_CONSTRAINT",
        )

    def _is_complement_candidate(
        self, message: str, pending: PendingResolution, semantic_signals: dict
    ) -> bool:
        """Retorna True se a mensagem parece complementar a pendência."""
        intent = semantic_signals.get("intent")
        product_term = semantic_signals.get("product_term") or ""
        pending_product = pending.product_term or ""
        brand = semantic_signals.get("explicit_brand")
        presentation = semantic_signals.get("explicit_presentation")

        # Precisa ter alguma constraint
        if not brand and not presentation:
            return False

        # Intent diferente de ADD_ITEM → não é complemento
        if intent and intent != "ADD_ITEM":
            return False

        # Verbo de nova operação no início → não é complemento
        msg_lower = message.lower().strip()
        for verb in self.NEW_OPERATION_VERBS:
            if msg_lower.startswith(verb):
                return False

        # Product term claramente diferente do pending → nova operação
        if product_term and pending_product:
            pt_lower = product_term.lower().strip()
            pp_lower = pending_product.lower().strip()
            if len(pt_lower) > 3 and pt_lower not in pp_lower and pp_lower not in pt_lower:
                return False

        return True

    def _extract_constraints(self, semantic_signals: dict) -> dict:
        constraints = {}
        brand = semantic_signals.get("explicit_brand")
        presentation = semantic_signals.get("explicit_presentation")
        if brand:
            constraints["brand"] = self._normalize_brand(brand)
        if presentation:
            constraints["presentation"] = presentation.lower().strip()
        return constraints

    def _normalize_brand(self, brand: str) -> str:
        """Remove prefixos como 'da', 'do', 'de' do nome da marca."""
        return re.sub(r'^(da|do|de)\s+', '', brand.strip(), flags=re.IGNORECASE)

    def _apply_constraints(
        self, pending: PendingResolution, constraints: dict
    ) -> PendingResolution:
        updated = copy.deepcopy(pending)
        if "brand" in constraints:
            updated.brand = constraints["brand"]
            if "brand" in updated.missing_fields:
                updated.missing_fields = [
                    f for f in updated.missing_fields if f != "brand"
                ]
        if "presentation" in constraints:
            updated.presentation = constraints["presentation"]
            if "presentation" in updated.missing_fields:
                updated.missing_fields = [
                    f for f in updated.missing_fields if f != "presentation"
                ]
        return updated