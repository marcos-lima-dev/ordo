import re
import json
from pathlib import Path
from .base import CandidateAdapter, register_adapter

@register_adapter("deterministic")
class DeterministicAdapter(CandidateAdapter):
    def __init__(self):
        self.catalog = self._load_catalog()
        self.brands = self._extract_brands()
        self.presentation_terms = {
            "forma", "formas", "barra", "barras", "bloco", "blocos",
            "bisnaga", "bisnagas", "peça", "peças", "cartela", "cartelas",
            "pote", "potes", "saco", "sacos", "garrafa", "garrafas",
            "caixa", "caixas", "balde", "baldes", "pacote", "pacotes",
            "fração", "frações", "meia forma", "1/2 forma", "1/8", "triângulo",
            "vácuo", "unidade"
        }
        self.unit_terms = {
            "kg": "KG",
            "quilos": "KG",
            "kilo": "KG",
            "g": "G",
            "gramas": "G",
            "l": "L",
            "litros": "L",
        }

    def _load_catalog(self):
        catalog_path = Path("data/catalog.json")
        with open(catalog_path) as f:
            return json.load(f)

    def _extract_brands(self):
        brands = set()
        for p in self.catalog:
            if p["brand"] not in ("DESCONHECIDO", "NÃO INFORMADO"):
                brands.add(p["brand"].lower())
        return brands

    def predict(self, message: str) -> dict:
        original = message.lower().strip()

        intent = self._determine_intent(original)
        quantity_value, quantity_origin, unit, unit_origin = self._extract_quantity_unit(original)
        product_term = self._extract_product_term(original)
        explicit_presentation = self._extract_presentation(original)
        explicit_brand = self._extract_brand(original)
        contextual_references = self._extract_contextual(original)
        candidates, resolution_status = self._resolve_product(
            product_term, explicit_brand, explicit_presentation
        )
        missing_info = self._determine_missing(
            quantity_value, unit, explicit_brand, explicit_presentation,
            product_term, resolution_status
        )

        return {
            "intent": intent,
            "product_term": product_term,
            "quantity": {
                "value": quantity_value,
                "value_origin": quantity_origin,
                "unit": unit,
                "unit_origin": unit_origin,
            },
            "explicit_presentation": explicit_presentation,
            "explicit_brand": explicit_brand,
            "contextual_references": contextual_references,
            "missing_information": missing_info,
            "catalog_candidates": candidates,
            "product_resolution_status": resolution_status,
        }

    def _determine_intent(self, text: str) -> str:
        if any(w in text for w in ["quero", "me manda", "coloca", "gostaria", "manda"]):
            return "ADD_ITEM"
        if any(w in text for w in ["tira", "remove", "cancela", "cancelar"]):
            if "pedido" in text or "tudo" in text:
                return "CANCEL_ORDER"
            return "REMOVE_ITEM"
        if any(w in text for w in ["muda", "troca", "substitui"]):
            return "REPLACE_ITEM"
        if any(w in text for w in ["fecha", "confirmar", "confirmado", "pode fechar"]):
            return "CONFIRM_ORDER"
        if any(w in text for w in ["quanto", "preço", "valor"]):
            return "QUERY_PRICE"
        if any(w in text for w in ["tem", "estoque", "disponível"]):
            return "QUERY_AVAILABILITY"
        return "UNKNOWN"

    def _extract_quantity_unit(self, text: str):
        cleaned = re.sub(r'\b(da|de|do|das|dos)\b', '', text)
        number_match = re.search(r'(\d+(?:[.,]\d+)?)', cleaned)
        if number_match:
            value_str = number_match.group(1).replace(',', '.')
            value = float(value_str)
            origin = "EXPLICIT"
            rest = cleaned[number_match.end():].strip()
            unit, unit_origin = self._extract_unit_from_text(rest)
            return value, origin, unit, unit_origin
        else:
            number_words = {
                "um": 1, "uma": 1, "dois": 2, "duas": 2,
                "três": 3, "quatro": 4, "cinco": 5, "seis": 6,
                "sete": 7, "oito": 8, "nove": 9, "dez": 10
            }
            for word, val in number_words.items():
                if re.search(r'\b' + word + r'\b', text):
                    return val, "EXPLICIT", None, "NOT_INFORMED"
            return None, "NOT_INFORMED", None, "NOT_INFORMED"

    def _extract_unit_from_text(self, text: str):
        for key, unit in self.unit_terms.items():
            if text.startswith(key) or re.search(r'\b' + key + r'\b', text):
                return unit, "EXPLICIT"
        for term in self.presentation_terms:
            if re.search(r'\b' + term + r'\b', text):
                return term, "EXPLICIT"
        return None, "NOT_INFORMED"

    def _extract_product_term(self, text: str):
        cleaned = text
        cleaned = re.sub(r'\d+(?:[.,]\d+)?', '', cleaned)
        for unit in self.unit_terms.keys():
            cleaned = re.sub(r'\b' + re.escape(unit) + r'\b', '', cleaned, flags=re.IGNORECASE)
        for term in self.presentation_terms:
            cleaned = re.sub(r'\b' + re.escape(term) + r'\b', '', cleaned, flags=re.IGNORECASE)
        for brand in self.brands:
            cleaned = re.sub(r'\b' + re.escape(brand) + r'\b', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\b(quero|me manda|coloca|gostaria|manda|tira|remove|troca|fecha|quanto|tem)\b', '', cleaned)
        cleaned = re.sub(r'\b(da|de|do|das|dos|a|o|as|os)\b', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned if cleaned else None

    def _extract_presentation(self, text: str):
        for term in self.presentation_terms:
            if re.search(r'\b' + re.escape(term) + r'\b', text, re.IGNORECASE):
                return term
        return None

    def _extract_brand(self, text: str):
        for brand in self.brands:
            if re.search(r'\b' + re.escape(brand) + r'\b', text, re.IGNORECASE):
                return brand.title()
        return None

    def _extract_contextual(self, text: str):
        refs = []
        if re.search(r'\b(daquele|desse|deste|daquela|dessa|desta|do outro|do mesmo)\b', text):
            refs.append("daquele")
        if re.search(r'\b(mais|novamente|de novo)\b', text):
            refs.append("mais")
        return refs

    def _resolve_product(self, product_term, brand, presentation):
        if not product_term:
            return [], "NOT_FOUND"
        term_lower = product_term.lower()
        candidates = []
        for p in self.catalog:
            name_lower = p["normalized_name"].lower()
            if brand:
                brand_lower = brand.lower()
                if brand_lower not in name_lower:
                    continue
            if presentation:
                pres_lower = presentation.lower()
                if pres_lower not in name_lower and pres_lower != p["apresentacao_individual"].lower():
                    continue
            if term_lower in name_lower or any(term_lower in a.lower() for a in [p.get("original_name", "")]):
                candidates.append(p["product_id"])
        candidates = list(set(candidates))
        if len(candidates) == 1:
            return candidates, "EXACT_MATCH"
        elif len(candidates) > 1:
            return candidates, "AMBIGUOUS"
        else:
            return [], "NOT_FOUND"

    def _determine_missing(self, quantity_value, unit, brand, presentation, product_term, resolution_status):
        missing = []
        if quantity_value is None:
            missing.append("quantity")
        if unit is None:
            missing.append("unit")
        if brand is None and resolution_status != "NOT_FOUND":
            missing.append("brand")
        if presentation is None and resolution_status == "AMBIGUOUS":
            missing.append("presentation")
        if product_term is None or len(product_term) < 3:
            missing.append("product_specification")
        return missing

    @property
    def name(self) -> str:
        return "DeterministicAdapter"