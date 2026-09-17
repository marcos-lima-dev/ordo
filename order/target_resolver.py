from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum

from order.state import OrderState, OrderItem

class TargetStatus(Enum):
    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    UNKNOWN = "UNKNOWN"

class TargetSource(Enum):
    EXPLICIT_ITEM_REFERENCE = "EXPLICIT_ITEM_REFERENCE"
    PENDING_REFERENCE = "PENDING_REFERENCE"
    CONTEXTUAL_REFERENCE = "CONTEXTUAL_REFERENCE"
    UNIQUE_ORDER_ITEM_MATCH = "UNIQUE_ORDER_ITEM_MATCH"
    ACTIVE_CONTEXT = "ACTIVE_CONTEXT"
    UNKNOWN = "UNKNOWN"

@dataclass
class TargetResult:
    status: TargetStatus
    target_item_id: Optional[str] = None
    evidence: List[str] = field(default_factory=list)
    source: TargetSource = TargetSource.UNKNOWN
    reason_code: Optional[str] = None  # usado quando status != RESOLVED

class TargetResolver:
    def resolve(
        self,
        message: str,
        state: OrderState,
        reference_product_term: Optional[str] = None,
        ref_signal: Any = None,
    ) -> TargetResult:
        """
        Resolve o target de uma operação que atua sobre item existente.
        Prioriza: referência explícita > pending > contexto > único match.
        """
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

        # 4. Único item compatível (sem menção explícita)
        if len(state.items) == 1:
            return TargetResult(
                status=TargetStatus.RESOLVED,
                target_item_id=state.items[0].id,
                evidence=["unique_order_item_match"],
                source=TargetSource.UNIQUE_ORDER_ITEM_MATCH,
            )

        # 5. Sem evidência suficiente
        return TargetResult(
            status=TargetStatus.UNKNOWN,
            evidence=["no sufficient evidence"],
            source=TargetSource.UNKNOWN,
            reason_code="MISSING_TARGET",
        )