from typing import Optional
from order.state import OrderState
from order.reference_signal import ReferenceSignal, ReferenceType

class ReferenceResolver:
    def resolve(self, message: str, state: Optional[OrderState] = None) -> ReferenceSignal:
        msg_lower = message.lower()
        
        if state is None:
            return ReferenceSignal(
                type=ReferenceType.UNKNOWN,
                requires_clarification=True,
                evidence=["NO_STATE"]
            )
        
        # 1. Referência explícita a um produto existente
        #    Usamos product_term como identificador
        for item in state.items:
            if item.product_term and item.product_term in msg_lower:
                # Se houver mais de um item com o mesmo termo, isso pode ser ambíguo
                # Por enquanto, selecionamos o primeiro, mas isso deve ser refinado
                return ReferenceSignal(
                    type=ReferenceType.EXPLICIT_REFERENCE,
                    product_term=item.product_term,  # usamos product_term como identificador
                    constraints={},  # poderíamos extrair constraints adicionais
                    evidence=["EXPLICIT_PRODUCT_REFERENCE"]
                )
        
        # 2. Referência a item pendente
        if state.pending_resolution:
            pending = state.pending_resolution
            brand = self._extract_brand(msg_lower)
            presentation = self._extract_presentation(msg_lower)
            if brand or presentation:
                constraints = {}
                if brand:
                    constraints["brand"] = brand
                if presentation:
                    constraints["presentation"] = presentation
                return ReferenceSignal(
                    type=ReferenceType.PENDING_REFERENCE,
                    constraints=constraints,
                    evidence=["PENDING_RESOLUTION", "EXPLICIT_CONSTRAINT"]
                )
            if self._is_confirmation(msg_lower):
                return ReferenceSignal(
                    type=ReferenceType.PENDING_REFERENCE,
                    evidence=["PENDING_RESOLUTION", "CONFIRMATION"]
                )
        
        # 3. Referência genérica
        if self._is_generic_reference(msg_lower):
            if state.items:
                # Evidência de recência: último item, mas isso precisa ser refinado
                last_item = state.items[-1]
                return ReferenceSignal(
                    type=ReferenceType.GENERIC_REFERENCE,
                    product_term=last_item.product_term,
                    constraints={},
                    evidence=["GENERIC_REFERENCE", "LAST_ITEM"]
                )
            else:
                return ReferenceSignal(
                    type=ReferenceType.UNKNOWN,
                    requires_clarification=True,
                    evidence=["GENERIC_REFERENCE_BUT_NO_ITEMS"]
                )
        
        # 4. Se há apenas um item, pode ser referência implícita
        if len(state.items) == 1:
            return ReferenceSignal(
                type=ReferenceType.EXPLICIT_REFERENCE,
                product_term=state.items[0].product_term,
                constraints={},
                evidence=["ONLY_ITEM"]
            )
        
        # 5. Caso contrário, sem referência clara
        return ReferenceSignal(
            type=ReferenceType.UNKNOWN,
            requires_clarification=True,
            evidence=["NO_CLEAR_REFERENCE"]
        )
    
    def _extract_brand(self, text: str) -> Optional[str]:
        brands = ["tânia", "coyote", "são vicente", "catupiry", "roseli", "larisol", "villani", "serta norte", "gran parma", "dona rosa"]
        for brand in brands:
            if brand in text:
                return brand.title()
        return None
    
    def _extract_presentation(self, text: str) -> Optional[str]:
        terms = ["forma", "bisnaga", "peça", "pote", "saco", "garrafa", "caixa", "barra", "bloco", "cartela", "balde", "pacote", "fração", "vácuo", "unidade"]
        for term in terms:
            if term in text:
                return term
        return None
    
    def _is_generic_reference(self, text: str) -> bool:
        return any(w in text for w in ["esse", "este", "aquele", "esse aqui", "aquele lá", "o outro", "esse último"])
    
    def _is_confirmation(self, text: str) -> bool:
        return any(w in text for w in ["é esse", "é este", "isso mesmo", "confirmo", "é isso"])