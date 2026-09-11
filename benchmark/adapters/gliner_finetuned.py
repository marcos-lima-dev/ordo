from gliner import GLiNER
from .base import CandidateAdapter, register_adapter

@register_adapter("gliner_ft")
class GLiNERFinetunedAdapter(CandidateAdapter):
    def __init__(self, model_path="./gliner_finetuned_model", device="cpu"):
        self.model_path = model_path
        self.device = device
        print(f"Carregando modelo fine-tunado de {model_path}...")
        self.model = GLiNER.from_pretrained(model_path)
        self.labels = ["produto", "marca", "apresentacao", "intencao"]

    def predict(self, message: str) -> dict:
        entities = self.model.predict_entities(message, self.labels, threshold=0.3)
        
        product = None
        brand = None
        presentation = None
        intent = "UNKNOWN"
        
        for ent in entities:
            label = ent["label"]
            text = ent["text"]
            if label == "produto":
                product = text
            elif label == "marca":
                brand = text
            elif label == "apresentacao":
                presentation = text
            elif label == "intencao":
                intent = self._map_intent(text)
        
        if intent == "UNKNOWN":
            intent = self._fallback_intent(message)
        
        quantity = {
            "value": None,
            "value_origin": "NOT_INFORMED",
            "unit": None,
            "unit_origin": "NOT_INFORMED"
        }
        
        return {
            "intent": intent,
            "product_term": product,
            "quantity": quantity,
            "explicit_presentation": presentation,
            "explicit_brand": brand,
            "contextual_references": [],
            "missing_information": [],
            "catalog_candidates": [],
            "product_resolution_status": "NOT_FOUND"
        }

    def _map_intent(self, text: str) -> str:
        text_lower = text.lower()
        if "add" in text_lower or "adicionar" in text_lower:
            return "ADD_ITEM"
        if "remove" in text_lower or "remover" in text_lower:
            return "REMOVE_ITEM"
        if "change" in text_lower or "mudar" in text_lower or "alterar" in text_lower:
            return "CHANGE_QUANTITY"
        if "confirm" in text_lower or "confirmar" in text_lower:
            return "CONFIRM_ORDER"
        if "cancel" in text_lower or "cancelar" in text_lower:
            return "CANCEL_ORDER"
        return "UNKNOWN"

    def _fallback_intent(self, message: str) -> str:
        msg = message.lower()
        if any(w in msg for w in ["quero", "me manda", "coloca", "bota", "manda"]):
            return "ADD_ITEM"
        if any(w in msg for w in ["tira", "remove", "cancela"]):
            return "REMOVE_ITEM"
        if any(w in msg for w in ["muda", "troca", "na verdade"]):
            return "CHANGE_QUANTITY"
        if any(w in msg for w in ["fecha", "fechar", "confirmar"]):
            return "CONFIRM_ORDER"
        if any(w in msg for w in ["cancela tudo", "cancelar pedido"]):
            return "CANCEL_ORDER"
        return "UNKNOWN"

    @property
    def name(self) -> str:
        return "GLiNER-Finetuned"