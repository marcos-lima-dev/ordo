from dataclasses import dataclass, field
from typing import Optional, List, Any
from enum import Enum
import re

from order.state import OrderState


class TargetStatus(Enum):
    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    UNKNOWN = "UNKNOWN"


class TargetSource(Enum):
    EXPLICIT_ITEM_REFERENCE = "EXPLICIT_ITEM_REFERENCE"
    PENDING_REFERENCE = "PENDING_REFERENCE"
    CONTEXTUAL_REFERENCE = "CONTEXTUAL_REFERENCE"
    UNIQUE_ORDER_ITEM_MATCH = "UNIQUE_ORDER_ITEM_MATCH"
    MESSAGE_TOKEN_OVERLAP = "MESSAGE_TOKEN_OVERLAP"
    UNKNOWN = "UNKNOWN"


@dataclass
class TargetResult:
    status: TargetStatus
    target_item_id: Optional[str] = None
    evidence: List[str] = field(default_factory=list)
    source: TargetSource = TargetSource.UNKNOWN
    reason_code: Optional[str] = None


class TargetResolver:
    """
    Resolve o target de uma operação que atua sobre item existente.
    Prioriza: referência explícita > pending > contexto > token overlap > único match.
    """

    STOPWORDS = {
        "para", "pelo", "pela", "com", "sem", "mais", "esse", "esta",
        "isso", "aqui", "depois", "antes", "então", "também",
        "quero", "manda", "coloca", "tira", "remove", "muda", "troca",
        "substitui", "bota", "adiciona", "cancela", "fecha",
    }

    def resolve(
        self,
        message: str,
        state: OrderState,
        reference_product_term: Optional[str] = None,
        ref_signal: Any = None,
    ) -> TargetResult:
        msg_lower = message.lower()

        # 1. Referência explícita ao produto
        if reference_product_term:
            matches = [
                item for item in state.items
                if reference_product_term.lower() in item.product_term.lower()
            ]
            if len(matches) == 1:
                return TargetResult(
                    status=TargetStatus.RESOLVED,
                    target_item_id=matches[0].id,
                    evidence=[f"explicit_match: {reference_product_term}"],
                    source=TargetSource.EXPLICIT_ITEM_REFERENCE,
                )
            if len(matches) > 1:
                return TargetResult(
                    status=TargetStatus.AMBIGUOUS,
                    evidence=[f"multiple matches for: {reference_product_term}"],
                    source=TargetSource.EXPLICIT_ITEM_REFERENCE,
                    reason_code="AMBIGUOUS_TARGET",
                )

        # 2. Referência pendente
        if state.pending_resolution and state.pending_resolution.product_term:
            pending_term = state.pending_resolution.product_term.lower()
            matches = [
                item for item in state.items
                if pending_term in item.product_term.lower()
            ]
            if len(matches) == 1:
                return TargetResult(
                    status=TargetStatus.RESOLVED,
                    target_item_id=matches[0].id,
                    evidence=[f"pending_match: {pending_term}"],
                    source=TargetSource.PENDING_REFERENCE,
                )
            if len(matches) > 1:
                return TargetResult(
                    status=TargetStatus.AMBIGUOUS,
                    evidence=[f"multiple pending matches: {pending_term}"],
                    source=TargetSource.PENDING_REFERENCE,
                    reason_code="AMBIGUOUS_TARGET",
                )

        # 3. Referência contextual genérica
        generic_terms = ["esse", "este", "aquele", "o outro", "o mesmo"]
        if any(term in msg_lower for term in generic_terms):
            if len(state.items) == 1:
                return TargetResult(
                    status=TargetStatus.RESOLVED,
                    target_item_id=state.items[0].id,
                    evidence=["generic_reference + single item"],
                    source=TargetSource.CONTEXTUAL_REFERENCE,
                )
            return TargetResult(
                status=TargetStatus.AMBIGUOUS,
                evidence=["generic_reference + multiple items"],
                source=TargetSource.CONTEXTUAL_REFERENCE,
                reason_code="AMBIGUOUS_TARGET",
            )

        # 4. Único item compatível
        if len(state.items) == 1:
            return TargetResult(
                status=TargetStatus.RESOLVED,
                target_item_id=state.items[0].id,
                evidence=["unique_order_item_match"],
                source=TargetSource.UNIQUE_ORDER_ITEM_MATCH,
            )

        # 5. Match contra tokens da mensagem original (robustez a ruído do GLiNER)
        if state.items:
            msg_tokens = self._significant_tokens(msg_lower)
            matches = []
            for item in state.items:
                item_tokens = self._significant_tokens(item.product_term.lower())
                if msg_tokens & item_tokens:
                    matches.append(item.id)
            if len(matches) == 1:
                return TargetResult(
                    status=TargetStatus.RESOLVED,
                    target_item_id=matches[0],
                    evidence=[f"token_overlap: {msg_tokens & self._significant_tokens(next(i for i in state.items if i.id == matches[0]).product_term.lower())}"],
                    source=TargetSource.MESSAGE_TOKEN_OVERLAP,
                )
            if len(matches) > 1:
                return TargetResult(
                    status=TargetStatus.AMBIGUOUS,
                    evidence=[f"multiple_token_matches: {len(matches)}"],
                    source=TargetSource.MESSAGE_TOKEN_OVERLAP,
                    reason_code="AMBIGUOUS_TARGET",
                )

        # 6. Múltiplos itens sem referência suficiente → AMBIGUOUS
        if len(state.items) > 1:
            return TargetResult(
                status=TargetStatus.AMBIGUOUS,
                evidence=["multiple_items_no_reference"],
                source=TargetSource.UNKNOWN,
                reason_code="AMBIGUOUS_TARGET",
            )

        # 7. Sem itens no estado
        return TargetResult(
            status=TargetStatus.UNKNOWN,
            evidence=["no_items_in_state"],
            source=TargetSource.UNKNOWN,
            reason_code="MISSING_TARGET",
        )

    def _significant_tokens(self, text: str) -> set:
        """Extrai tokens significativos (>= 4 chars, não stopwords)."""
        tokens = set(re.findall(r'\b[a-záéíóúãõçâêôûî]{4,}\b', text))
        return tokens - self.STOPWORDS