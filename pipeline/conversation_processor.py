from typing import Optional, Dict, Any
from order.state import OrderState, OrderItem
from order.pending import PendingResolution
from order.target import Target, TargetType
from pipeline.reference_resolver import ReferenceResolver
from benchmark.adapters.modular import ModularAdapter
from order.catalog_retriever import CatalogRetriever
from order.product_resolver import ProductResolver, ResolutionStatus

class ConversationProcessor:
    def __init__(self):
        self.adapter = ModularAdapter()
        self.resolver = ReferenceResolver()
        self.catalog_retriever = CatalogRetriever()
        self.product_resolver = ProductResolver()

    def process(self, message: str, state: OrderState) -> Dict[str, Any]:
        # 1. Interpretação bruta
        interpretation = self.adapter.predict(message)
        intent = interpretation["intent"]
        product_term = interpretation["product_term"]
        brand = interpretation["explicit_brand"]
        presentation = interpretation["explicit_presentation"]
        candidates = interpretation["catalog_candidates"]
        resolution_status = interpretation["product_resolution_status"]

        # 2. Resolve Target (Referências contextuais)
        target = self.resolver.resolve(message, state)

        # 3. Se target for um item existente ou pendente, aplica restrições
        if target.type == TargetType.PENDING_ITEM and target.brand_constraint:
            # Refina candidatos com a marca
            candidates = self.catalog_retriever.retrieve_with_constraints(
                product_term or "",
                brand=target.brand_constraint,
                presentation=presentation
            )
            resolution_status = self.product_resolver.resolve(candidates, product_term=product_term, brand=target.brand_constraint)

        elif target.type == TargetType.EXISTING_ITEM and target.item_id:
            # Para alteração de quantidade, usamos o item_id
            pass  # será tratado na transição

        # 4. Aplica a transição de estado
        new_state = self._apply_transition(state, intent, product_term, candidates, resolution_status, target, message)

        # 5. Resumo da operação
        return {
            "interpretation": interpretation,
            "target": target,
            "new_state": new_state.to_dict(),
            "action": self._describe_action(intent, product_term, target)
        }

    def _apply_transition(self, state: OrderState, intent: str, product_term: Optional[str],
                          candidates: list, resolution_status: str, target: Target, message: str) -> OrderState:
        if intent == "ADD_ITEM":
            if product_term:
                # Verifica se já existe um item pendente com o mesmo termo
                if state.pending_resolution and state.pending_resolution.product_term == product_term:
                    # Completa a pendência com a informação atual (marca, apresentação)
                    # Mas aqui só adicionamos como item resolvido
                    pass

                item = OrderItem(
                    product_term=product_term,
                    quantity=None,  # será extraído pelo adapter, mas aqui não temos
                    unit=None,
                    brand=target.brand_constraint if target.type == TargetType.PENDING_ITEM else None,
                    presentation=None,
                    resolved=(resolution_status == ResolutionStatus.EXACT_MATCH),
                    needs_clarification=(resolution_status in [ResolutionStatus.AMBIGUOUS, ResolutionStatus.NOT_FOUND]),
                    clarification_questions=[] if resolution_status == ResolutionStatus.EXACT_MATCH else ["product_specification"]
                )
                state.add_item(item)
            else:
                # Se não tem produto, mas tem target pendente, tenta resolver
                if target.type == TargetType.PENDING_ITEM and target.brand_constraint:
                    # Criar um item com base na pendência (mas não temos a pendência aqui)
                    pass
                else:
                    # Produto não identificado
                    pending = PendingResolution(
                        product_term=product_term or "produto não identificado",
                        quantity=None,
                        unit=None,
                        brand=target.brand_constraint if target.type == TargetType.PENDING_ITEM else None,
                        presentation=None,
                        missing_fields=["product_specification"],
                        reason="NOT_FOUND"
                    )
                    state.set_pending(pending)

        elif intent == "REMOVE_ITEM":
            if target.type == TargetType.EXISTING_ITEM and target.item_id:
                # Remove o item específico
                # Como não temos id, removemos o último item (simplificação)
                if state.items:
                    state.remove_item(-1)
            elif state.items:
                state.remove_item(-1)

        elif intent == "CHANGE_QUANTITY":
            # Identifica o item alvo
            target_item = None
            if target.type == TargetType.EXISTING_ITEM and target.item_id:
                # Encontra o item pelo id (não temos id, usamos index)
                pass
            elif state.items:
                # Por enquanto, altera o último item
                if state.items:
                    # Extrai nova quantidade da mensagem (usando regex simples)
                    import re
                    match = re.search(r'(\d+(?:[.,]\d+)?)', message)
                    if match:
                        new_qty = float(match.group(1).replace(',', '.'))
                        state.items[-1].quantity = new_qty
                        state.items[-1].resolved = True

        elif intent == "CONFIRM_ORDER":
            if state.pending_resolution is None and not any(item.needs_clarification for item in state.items):
                state.status = "CONFIRMED"
            else:
                state.status = "NEEDS_CLARIFICATION"

        elif intent == "CANCEL_ORDER":
            state.status = "CANCELED"
            state.items = []

        return state

    def _describe_action(self, intent: str, product_term: Optional[str], target: Target) -> str:
        if intent == "ADD_ITEM":
            return f"Adicionar item: {product_term or 'produto não identificado'}"
        elif intent == "REMOVE_ITEM":
            return f"Remover item: {target.item_id or 'último'}"
        elif intent == "CHANGE_QUANTITY":
            return "Alterar quantidade"
        elif intent == "CONFIRM_ORDER":
            return "Confirmar pedido"
        elif intent == "CANCEL_ORDER":
            return "Cancelar pedido"
        return "Ação desconhecida"