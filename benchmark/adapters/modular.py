import re
from pathlib import Path
from typing import Optional
from gliner import GLiNER
from transformers import pipeline
from .base import CandidateAdapter, register_adapter
from order.catalog_retriever import CatalogRetriever
from order.product_resolver import ProductResolver, ResolutionStatus

@register_adapter("modular")
class ModularAdapter(CandidateAdapter):
    """
    Adapter modular que combina:
    - GLiNER para extração de entidades (produto, marca, apresentação)
    - Classificador de intenção treinado
    - CatalogRetriever para recuperação de candidatos (fonte principal)
    - ProductResolver para status de resolução
    - Fallback com regras para casos não cobertos
    """

    def __init__(self, device="cpu"):
        self.device = device
        print("Carregando GLiNER...")
        self.gliner = GLiNER.from_pretrained("urchade/gliner_medium")
        self.entity_labels = ["produto", "marca", "apresentacao"]
        
        # Mapeamento de labels do classificador para intenções
        self.intent_label_map = {
            "LABEL_0": "ADD_ITEM",
            "LABEL_1": "REMOVE_ITEM",
            "LABEL_2": "CHANGE_QUANTITY",
            "LABEL_3": "CONFIRM_ORDER",
            "LABEL_4": "CANCEL_ORDER",
            "LABEL_5": "UNKNOWN"
        }
        
        # Tenta carregar o classificador de intenção se existir
        self.intent_classifier = None
        classifier_path = Path("models/intent_classifier")
        if classifier_path.exists():
            print("Carregando classificador de intenção treinado...")
            try:
                self.intent_classifier = pipeline(
                    "text-classification",
                    model=str(classifier_path),
                    device=0 if device == "cuda" else -1
                )
                print("Classificador carregado com sucesso.")
            except Exception as e:
                print(f"Erro ao carregar classificador: {e}. Usando fallback.")
                self.intent_classifier = None
        else:
            print("Classificador de intenção não encontrado. Usando fallback.")
            self.intent_classifier = None
        
        # CatalogRetriever e ProductResolver
        self.catalog_retriever = CatalogRetriever()
        self.product_resolver = ProductResolver()

    def predict(self, message: str) -> dict:
        # 1. Extrai entidades com GLiNER (sinal auxiliar)
        entities = self.gliner.predict_entities(message, self.entity_labels, threshold=0.3)
        
        product_raw = None
        brand = None
        presentation = None
        
        for ent in entities:
            label = ent["label"]
            text = ent["text"]
            if label == "produto":
                product_raw = text
            elif label == "marca":
                brand = text
            elif label == "apresentacao":
                presentation = text

        # 2. Classifica intenção
        intent = self._classify_intent(message)

        # 3. Recupera candidatos do catálogo usando a mensagem COMPLETA
        candidates = self.catalog_retriever.retrieve_with_constraints(
            message,
            brand=brand,
            presentation=presentation
        )
        
        # 4. Se houver exatamente 1 candidato, usa o nome normalizado como product_term
        if len(candidates) == 1:
            product_id = candidates[0]
            product = self.catalog_retriever._get_product_by_id(product_id)
            if product:
                product_raw = product["normalized_name"]
        
        # 5. Resolve status do produto
        resolution_status = self.product_resolver.resolve(candidates, product_term=product_raw, brand=brand)

        # 6. Extrai quantidade com regex (independente do GLiNER)
        qty_value, qty_unit = self._extract_quantity(message)
        if qty_value is not None:
            qty_origin = "EXPLICIT"
            unit_origin = "EXPLICIT" if qty_unit else "NOT_INFORMED"
        else:
            qty_origin = "NOT_INFORMED"
            unit_origin = "NOT_INFORMED"

        quantity = {
            "value": qty_value,
            "value_origin": qty_origin,
            "unit": qty_unit,
            "unit_origin": unit_origin
        }

        # 7. Determina missing_information com base no status
        missing_info = []
        if not product_raw:
            missing_info.append("product_specification")
        if resolution_status == ResolutionStatus.AMBIGUOUS:
            missing_info.append("product_specification")
        if not brand and resolution_status == ResolutionStatus.AMBIGUOUS:
            missing_info.append("brand")
        if not presentation and resolution_status == ResolutionStatus.AMBIGUOUS:
            missing_info.append("presentation")

        return {
            "intent": intent,
            "product_term": product_raw,
            "quantity": quantity,
            "explicit_presentation": presentation,
            "explicit_brand": brand,
            "contextual_references": [],
            "missing_information": missing_info,
            "catalog_candidates": candidates,
            "product_resolution_status": resolution_status
        }

    def _extract_quantity(self, message: str) -> tuple:
        """Extrai quantidade e unidade da mensagem usando regex."""
        # Padrão 1: número + unidade (ex: 10kg, 5 quilos)
        # Padrão 2: número sozinho (ex: "são 3", "muda para 4")
        patterns = [
            r'(\d+(?:[.,]\d+)?)\s*(kg|quilos|quilo|k|g|gramas|l|litros|forma|formas|peça|peças|pote|potes|saco|sacolas|garrafa|garrafas|caixa|caixas|barra|barras|bloco|blocos|bisnaga|bisnagas|cartela|cartelas|balde|baldes|pacote|pacotes)',
            r'(\d+(?:[.,]\d+)?)\s*(KG|QUILOS|G|L)',
            r'\b(\d+(?:[.,]\d+)?)\b(?!\s*(?:kg|quilos|g|gramas|l|litros))'  # número sem unidade
        ]
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                value = float(match.group(1).replace(',', '.'))
                # Se encontrou unidade no grupo 2, usa; senão unit=None
                unit = None
                if len(match.groups()) > 1 and match.group(2):
                    unit = match.group(2).lower()
                    unit_map = {
                        'kg': 'KG', 'quilos': 'KG', 'quilo': 'KG', 'k': 'KG',
                        'g': 'G', 'gramas': 'G',
                        'l': 'L', 'litros': 'L',
                        'forma': 'forma', 'formas': 'forma',
                        'peça': 'peça', 'peças': 'peça',
                        'pote': 'pote', 'potes': 'pote',
                        'saco': 'saco', 'sacolas': 'saco',
                        'garrafa': 'garrafa', 'garrafas': 'garrafa',
                        'caixa': 'caixa', 'caixas': 'caixa',
                        'barra': 'barra', 'barras': 'barra',
                        'bloco': 'bloco', 'blocos': 'bloco',
                        'bisnaga': 'bisnaga', 'bisnagas': 'bisnaga',
                        'cartela': 'cartela', 'cartelas': 'cartela',
                        'balde': 'balde', 'baldes': 'balde',
                        'pacote': 'pacote', 'pacotes': 'pacote',
                    }
                    unit = unit_map.get(unit, unit.upper())
                return value, unit
        return None, None

    def _classify_intent(self, message: str) -> str:
        if self.intent_classifier:
            try:
                result = self.intent_classifier(message)[0]
                label = result["label"]
                if label in self.intent_label_map:
                    return self.intent_label_map[label]
                return "UNKNOWN"
            except Exception:
                pass

        # Fallback com regras
        msg = message.lower()
        # Padrões contextuais para intenções implícitas
        if re.search(r'muda\s*para\s*\d+', msg):
            return "CHANGE_QUANTITY"
        if re.search(r'tira\s*\d+', msg):
            return "REMOVE_ITEM"
        if re.search(r'coloca\s*\d+\s*(?:kg|quilos|g|gramas|forma|peça|pote|saco|garrafa|caixa|barra|bloco|bisnaga)', msg):
            return "ADD_ITEM"
        if any(w in msg for w in ["quero", "me manda", "coloca", "bota", "manda", "gostaria"]):
            return "ADD_ITEM"
        if any(w in msg for w in ["tira", "remove", "cancela"]):
            if "tudo" in msg or "pedido" in msg:
                return "CANCEL_ORDER"
            return "REMOVE_ITEM"
        if any(w in msg for w in ["muda", "troca", "na verdade"]):
            return "CHANGE_QUANTITY"
        if any(w in msg for w in ["fecha", "fechar", "confirmar", "confirmado"]):
            return "CONFIRM_ORDER"
        return "UNKNOWN"

    @property
    def name(self) -> str:
        return "ModularAdapter"