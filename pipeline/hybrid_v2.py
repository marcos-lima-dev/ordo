from typing import Optional, Dict, Any
from benchmark.adapters import TucanoAdapter, DeterministicAdapter
from order.state import OrderState, OrderItem
from order.pending import PendingResolution
from pipeline.context_analyzer import ContextAnalyzer

class HybridPipelineV2:
    """
    Versão 2 do pipeline híbrido:
    - Usa Prompt V2 para o LLM.
    - Usa ContextAnalyzer para enriquecer a interpretação com contexto.
    - Gerencia pending_resolution para referências e ambiguidades.
    """

    def __init__(self, llm_model_size="0.5B"):
        self.llm = TucanoAdapter(model_size=llm_model_size)
        self.resolver = DeterministicAdapter()

    def process(self, message: str, state: Optional[OrderState] = None) -> Dict[str, Any]:
        if state is None:
            state = OrderState()

        # 1. LLM interpreta a mensagem (usando Prompt V2)
        raw_interpretation = self.llm.predict(message)

        # 2. ContextAnalyzer enriquece com contexto
        interpretation = ContextAnalyzer.analyze(message, state, raw_interpretation)

        # 3. Aplica resolução determinística (catálogo, status)
        interpretation = self._resolve_catalog(interpretation)

        # 4. Atualiza estado
        new_state = self._update_state(state, interpretation, message)

        return {
            "interpretation": interpretation,
            "state": new_state.to_dict(),
        }

    def _resolve_catalog(self, interpretation: dict) -> dict:
        product_term = interpretation.get("product_term")
        brand = interpretation.get("explicit_brand")
        presentation = interpretation.get("explicit_presentation")
        if product_term:
            candidates, status = self.resolver._resolve_product(product_term, brand, presentation)
            interpretation["catalog_candidates"] = candidates
            interpretation["product_resolution_status"] = status
        return interpretation

    def _update_state(self, state: OrderState, interpretation: dict, message: str) -> OrderState:
        intent = interpretation.get("intent")
        status = interpretation.get("product_resolution_status")
        product_term = interpretation.get("product_term")

        # Caso 1: Se há uma resolução pendente e a mensagem a complementa
        if state.pending_resolution and status == "HIGH_CONFIDENCE":
            pending = state.pending_resolution
            # Cria o item a partir da resolução pendente + complementos
            item = OrderItem(
                product_term=pending.product_term,
                quantity=pending.quantity or interpretation.get("quantity", {}).get("value"),
                unit=pending.unit or interpretation.get("quantity", {}).get("unit"),
                brand=pending.brand or interpretation.get("explicit_brand"),
                presentation=pending.presentation or interpretation.get("explicit_presentation"),
                resolved=True,
                needs_clarification=False,
            )
            state.add_item(item)
            state.clear_pending()
            return state

        # Caso 2: Adição de item
        if intent == "ADD_ITEM" and product_term:
            if status in ["AMBIGUOUS", "NOT_FOUND"]:
                # Cria uma resolução pendente
                pending = PendingResolution(
                    product_term=product_term,
                    quantity=interpretation.get("quantity", {}).get("value"),
                    unit=interpretation.get("quantity", {}).get("unit"),
                    brand=interpretation.get("explicit_brand"),
                    presentation=interpretation.get("explicit_presentation"),
                    missing_fields=interpretation.get("missing_information", []),
                    reason="AMBIGUOUS_PRODUCT" if status == "AMBIGUOUS" else "NOT_FOUND",
                )
                state.set_pending(pending)
                # Não adiciona item ainda, aguarda clarificação
            else:
                # Adiciona item resolvido
                item = OrderItem(
                    product_term=product_term,
                    quantity=interpretation.get("quantity", {}).get("value"),
                    unit=interpretation.get("quantity", {}).get("unit"),
                    brand=interpretation.get("explicit_brand"),
                    presentation=interpretation.get("explicit_presentation"),
                    resolved=(status == "EXACT_MATCH"),
                    needs_clarification=False,
                )
                state.add_item(item)

        # Caso 3: Alteração de quantidade
        elif intent == "CHANGE_QUANTITY" and state.items:
            # Por enquanto, altera o último item (futuramente, identificar alvo)
            new_quantity = interpretation.get("quantity", {}).get("value")
            if new_quantity is not None:
                state.items[-1].quantity = new_quantity

        # Caso 4: Remoção de item
        elif intent == "REMOVE_ITEM" and state.items:
            state.remove_item(-1)  # remove o último item (simplificado)

        # Caso 5: Confirmação (bloqueada se houver pendência)
        elif intent == "CONFIRM_ORDER":
            if state.pending_resolution is None:
                state.status = "CONFIRMED"
            else:
                # Não confirma, mantém pendente
                state.status = "NEEDS_CLARIFICATION"

        state.turn_count += 1
        state.last_message = message

        return state
