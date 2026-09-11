import re
from order.state import OrderState
from order.pending import PendingResolution

class ContextAnalyzer:
    """
    Analisa o contexto conversacional e enriquece a interpretação.
    Não força intenções; apenas adiciona informações contextuais quando seguras.
    """

    @staticmethod
    def analyze(message: str, state: OrderState, interpretation: dict) -> dict:
        """
        Recebe a mensagem, o estado atual e a interpretação crua do LLM.
        Retorna a interpretação enriquecida com contexto, se aplicável.
        """
        msg = message.lower().strip()
        pending = state.pending_resolution

        # 1. Se há uma resolução pendente, verifica se a mensagem a complementa
        if pending:
            # Tenta extrair marca (ex: "da Tânia", "da Coyote")
            brand_match = re.search(r'da\s+([A-Za-zÀ-ÖØ-öø-ÿ\s]+)', msg)
            if brand_match:
                brand = brand_match.group(1).strip()
                # Complementa a resolução pendente com a marca
                interpretation["explicit_brand"] = brand
                interpretation["product_term"] = pending.product_term
                if pending.quantity is not None:
                    interpretation["quantity"]["value"] = pending.quantity
                if pending.unit is not None:
                    interpretation["quantity"]["unit"] = pending.unit
                # Remove "brand" das lacunas
                if "brand" in interpretation.get("missing_information", []):
                    interpretation["missing_information"].remove("brand")
                if not interpretation["missing_information"]:
                    interpretation["product_resolution_status"] = "HIGH_CONFIDENCE"
                return interpretation

            # Tenta extrair apresentação (ex: "forma", "bisnaga")
            presentation_match = re.search(r'(forma|bisnaga|pote|caixa|garrafa|saco|barra|bloco|cartela|balde|pacote|fração|vácuo|unidade)', msg)
            if presentation_match:
                presentation = presentation_match.group(1)
                interpretation["explicit_presentation"] = presentation
                interpretation["product_term"] = pending.product_term
                if pending.quantity is not None:
                    interpretation["quantity"]["value"] = pending.quantity
                if pending.unit is not None:
                    interpretation["quantity"]["unit"] = pending.unit
                if "presentation" in interpretation.get("missing_information", []):
                    interpretation["missing_information"].remove("presentation")
                if not interpretation["missing_information"]:
                    interpretation["product_resolution_status"] = "HIGH_CONFIDENCE"
                return interpretation

        # 2. Detecção de alteração de quantidade (apenas se houver item identificável)
        if "na verdade" in msg or "muda" in msg or "troca" in msg:
            if state.items:
                # Verifica se há um item recente (por simplicidade, o último)
                # Futuramente pode ser mais sofisticado com identificação de alvo
                interpretation["intent"] = "CHANGE_QUANTITY"
                # Extrai a nova quantidade se presente
                quantity_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(kg|quilos|g|gramas|litros|l)?', msg)
                if quantity_match:
                    value = float(quantity_match.group(1).replace(',', '.'))
                    unit = quantity_match.group(2) if quantity_match.group(2) else None
                    if unit:
                        unit = unit.upper()
                    interpretation["quantity"]["value"] = value
                    interpretation["quantity"]["unit"] = unit
                    interpretation["quantity"]["value_origin"] = "EXPLICIT"
                return interpretation

        # 3. Detecção de confirmação (apenas se não houver pendências)
        if "pode fechar" in msg or "fecha" in msg:
            if state.pending_resolution is None:
                interpretation["intent"] = "CONFIRM_ORDER"
            else:
                # Se há pendência, não força confirmação
                interpretation["intent"] = "CONFIRM_ORDER"
                # Mantém estado de pendência (será bloqueado no pipeline)
            return interpretation

        return interpretation