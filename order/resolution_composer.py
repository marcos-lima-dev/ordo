from typing import Optional
from order.resolution_result import ResolutionResult, OutcomeType
from order.target_resolver import TargetStatus
from order.product_resolver import ResolutionStatus
from order.resolved_operation import OperationType


class ResolutionComposer:
    """
    Compõe o ResolutionResult (outcome + reason_code) a partir do estado das
    resoluções parciais (target, product, pending).

    Regra fundamental:
    - reason_code é consequência do estado da resolução, não de palavras da mensagem.
    - Campos N/A para uma operação não geram clarificação.
    """

    OPERATIONS_REQUIRING_TARGET = {
        OperationType.REMOVE_ITEM,
        OperationType.CHANGE_QUANTITY,
        OperationType.REPLACE_ITEM,
    }

    OPERATIONS_REQUIRING_PRODUCT = {
        OperationType.ADD_ITEM,
        OperationType.REPLACE_ITEM,
    }

    OPERATIONS_REQUIRING_QUANTITY = {
        OperationType.CHANGE_QUANTITY,
    }

    def compose(
        self,
        op_type: OperationType,
        target_status: Optional[TargetStatus] = None,
        target_reason: Optional[str] = None,
        product_status: Optional[str] = None,
        quantity_value: Optional[float] = None,
        pending_blocking: bool = False,
    ) -> Optional[ResolutionResult]:
        """
        Retorna None se a operação pode ser executada.
        Retorna ResolutionResult(NEEDS_CLARIFICATION, reason_code) se não pode.
        """

        # 1. Operação exige target?
        if op_type in self.OPERATIONS_REQUIRING_TARGET:
            if target_status == TargetStatus.UNKNOWN:
                return ResolutionResult(
                    outcome=OutcomeType.NEEDS_CLARIFICATION,
                    reason_code=target_reason or "MISSING_TARGET",
                )
            if target_status == TargetStatus.AMBIGUOUS:
                return ResolutionResult(
                    outcome=OutcomeType.NEEDS_CLARIFICATION,
                    reason_code=target_reason or "AMBIGUOUS_TARGET",
                )

        # 2. Operação exige produto novo?
        if op_type in self.OPERATIONS_REQUIRING_PRODUCT:
            if product_status == ResolutionStatus.NOT_FOUND:
                return ResolutionResult(
                    outcome=OutcomeType.NEEDS_CLARIFICATION,
                    reason_code="MISSING_PRODUCT",
                )
            if product_status == ResolutionStatus.AMBIGUOUS:
                return ResolutionResult(
                    outcome=OutcomeType.NEEDS_CLARIFICATION,
                    reason_code="AMBIGUOUS_PRODUCT",
                )

        # 3. Operação exige quantity?
        if op_type in self.OPERATIONS_REQUIRING_QUANTITY:
            if quantity_value is None:
                return ResolutionResult(
                    outcome=OutcomeType.NEEDS_CLARIFICATION,
                    reason_code="MISSING_QUANTITY",
                )

        # 4. Pending bloqueante?
        if pending_blocking:
            return ResolutionResult(
                outcome=OutcomeType.NEEDS_CLARIFICATION,
                reason_code="PENDING_RESOLUTION",
            )

        # Tudo ok
        return None