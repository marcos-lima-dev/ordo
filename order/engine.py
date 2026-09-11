from typing import Optional, Tuple, List
from order.resolved_operation import ResolvedOperation, OperationType
from order.state import OrderState, OrderItem
from order.order_status import OrderStatus, can_transition
from order.pending import PendingResolution

class OrderEngine:
    """
    Núcleo transacional do Ordo.
    Recebe um OrderState e uma ResolvedOperation, e produz um novo OrderState.
    É 100% determinístico, atômico e auditável.
    """

    def apply(self, state: OrderState, operation: ResolvedOperation) -> Tuple[OrderState, List[str]]:
        """
        Aplica uma operação ao estado e retorna (novo_estado, eventos).
        Se a operação for inválida, retorna o estado inalterado e uma lista de erros.
        """
        # Validação básica
        if not operation.is_valid():
            return state, ["Operação inválida: campos obrigatórios faltando"]

        # Estado terminal: confirmado ou cancelado não podem ser alterados
        if state.status in [OrderStatus.CONFIRMED.value, OrderStatus.CANCELLED.value]:
            return state, [f"Pedido já está {state.status}"]

        events = []

        # Roteia para o método específico
        if operation.type == OperationType.ADD_ITEM:
            return self._apply_add_item(state, operation, events)

        if operation.type == OperationType.REMOVE_ITEM:
            return self._apply_remove_item(state, operation, events)

        if operation.type == OperationType.CHANGE_QUANTITY:
            return self._apply_change_quantity(state, operation, events)

        if operation.type == OperationType.REPLACE_ITEM:
            return self._apply_replace_item(state, operation, events)

        if operation.type == OperationType.CONFIRM_ORDER:
            return self._apply_confirm_order(state, operation, events)

        if operation.type == OperationType.CANCEL_ORDER:
            return self._apply_cancel_order(state, operation, events)

        return state, ["Tipo de operação não suportado"]

    # =============================================
    # ADD_ITEM
    # =============================================
    def _apply_add_item(self, state: OrderState, op: ResolvedOperation, events: List[str]) -> Tuple[OrderState, List[str]]:
        # Cria o item
        item = OrderItem(
            product_term=op.product_term or "unknown",
            product_id=op.product_id,
            quantity=op.quantity_value,
            unit=op.quantity_unit,
            resolved=(op.product_id is not None),
            needs_clarification=(op.product_id is None),
            clarification_questions=[] if op.product_id else ["product_specification"]
        )
        state.add_item(item)

        # Se não houver product_id, cria uma pending_resolution
        if op.product_id is None:
            pending = PendingResolution(
                product_term=op.product_term or "unknown",
                quantity=op.quantity_value,
                unit=op.quantity_unit,
                missing_fields=["product_specification"],
                reason="NOT_FOUND"
            )
            state.set_pending(pending)
            state.status = OrderStatus.NEEDS_CLARIFICATION.value
        else:
            # Verifica se todos os itens estão resolvidos
            self._update_status(state)

        events.append("ITEM_ADDED")
        return state, events

    # =============================================
    # REMOVE_ITEM
    # =============================================
    def _apply_remove_item(self, state: OrderState, op: ResolvedOperation, events: List[str]) -> Tuple[OrderState, List[str]]:
        if op.target_item_id is None:
            return state, ["REMOVE_ITEM requer target_item_id"]

        # Busca o item pelo ID
        target = state.find_item_by_id(op.target_item_id)
        if target is None:
            return state, [f"Item {op.target_item_id} não encontrado"]

        # Remove o item
        if state.remove_item_by_id(op.target_item_id):
            events.append("ITEM_REMOVED")
            self._update_status(state)
            return state, events
        else:
            return state, [f"Falha ao remover item {op.target_item_id}"]

    # =============================================
    # CHANGE_QUANTITY
    # =============================================
    def _apply_change_quantity(self, state: OrderState, op: ResolvedOperation, events: List[str]) -> Tuple[OrderState, List[str]]:
        if op.target_item_id is None:
            return state, ["CHANGE_QUANTITY requer target_item_id"]

        if op.quantity_value is None:
            return state, ["CHANGE_QUANTITY requer quantity_value"]

        target = state.find_item_by_id(op.target_item_id)
        if target is None:
            return state, [f"Item {op.target_item_id} não encontrado"]

        # Atualiza a quantidade
        old_qty = target.quantity
        target.quantity = op.quantity_value
        if op.quantity_unit:
            target.unit = op.quantity_unit

        events.append("ITEM_QUANTITY_CHANGED")
        self._update_status(state)
        return state, events

    # =============================================
    # REPLACE_ITEM
    # =============================================
    def _apply_replace_item(self, state: OrderState, op: ResolvedOperation, events: List[str]) -> Tuple[OrderState, List[str]]:
        if op.target_item_id is None:
            return state, ["REPLACE_ITEM requer target_item_id"]

        if op.replacement_product_id is None:
            return state, ["REPLACE_ITEM requer replacement_product_id"]

        target = state.find_item_by_id(op.target_item_id)
        if target is None:
            return state, [f"Item {op.target_item_id} não encontrado"]

        # Substitui o produto
        old_product = target.product_term
        target.product_id = op.replacement_product_id
        target.product_term = op.product_term or "unknown"
        target.resolved = True
        target.needs_clarification = False
        target.clarification_questions = []

        events.append("ITEM_REPLACED")
        self._update_status(state)
        return state, events

    # =============================================
    # CONFIRM_ORDER
    # =============================================
    def _apply_confirm_order(self, state: OrderState, op: ResolvedOperation, events: List[str]) -> Tuple[OrderState, List[str]]:
        # Verifica se pode confirmar
        if state.pending_resolution is not None:
            return state, ["Confirmação bloqueada: existe resolução pendente"]

        for item in state.items:
            if item.needs_clarification:
                return state, [f"Confirmação bloqueada: item '{item.product_term}' precisa de clarificação"]

        # Atualiza o status
        if can_transition(OrderStatus(state.status), OrderStatus.CONFIRMED):
            state.status = OrderStatus.CONFIRMED.value
            events.append("ORDER_CONFIRMED")
        else:
            return state, [f"Não é possível confirmar a partir do estado {state.status}"]

        return state, events

    # =============================================
    # CANCEL_ORDER
    # =============================================
    def _apply_cancel_order(self, state: OrderState, op: ResolvedOperation, events: List[str]) -> Tuple[OrderState, List[str]]:
        if can_transition(OrderStatus(state.status), OrderStatus.CANCELLED):
            state.status = OrderStatus.CANCELLED.value
            events.append("ORDER_CANCELLED")
        else:
            return state, [f"Não é possível cancelar a partir do estado {state.status}"]

        return state, events

    # =============================================
    # Utilitários
    # =============================================
    def _update_status(self, state: OrderState) -> None:
        """Atualiza o status do pedido com base nos itens e pendências."""
        if state.pending_resolution is not None:
            state.status = OrderStatus.NEEDS_CLARIFICATION.value
            return

        for item in state.items:
            if item.needs_clarification:
                state.status = OrderStatus.NEEDS_CLARIFICATION.value
                return

        # Se não há pendências e há itens, está pronto para confirmar
        if state.items:
            state.status = OrderStatus.READY_TO_CONFIRM.value
        else:
            state.status = OrderStatus.DRAFT.value