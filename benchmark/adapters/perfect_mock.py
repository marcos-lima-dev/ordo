import json
from pathlib import Path
from .base import CandidateAdapter

class PerfectMockAdapter(CandidateAdapter):
    """
    Mock que retorna exatamente o expected do Golden Dataset.
    Usado para validar a infraestrutura.
    """

    def __init__(self):
        self._dataset = self._load_golden()
        self._lookup = {item["id"]: item["expected"] for item in self._dataset}

    def _load_golden(self):
        golden_path = Path("tests/golden_dataset.jsonl")
        dataset = []
        with open(golden_path) as f:
            for line in f:
                if line.strip():
                    dataset.append(json.loads(line))
        return dataset

    def predict(self, message: str) -> dict:
        # Procura o expected correspondente à mensagem
        for item in self._dataset:
            if item["input"] == message:
                return item["expected"].copy()  # evita mutação acidental
        # Se não encontrar, retorna algo padrão (não deve ocorrer)
        return {"intent": "UNKNOWN", "product_term": None, "quantity": {"value": None, "value_origin": "NOT_INFORMED", "unit": None, "unit_origin": "NOT_INFORMED"}, "explicit_presentation": None, "explicit_brand": None, "contextual_references": [], "missing_information": [], "catalog_candidates": [], "product_resolution_status": "NOT_FOUND"}

    @property
    def name(self) -> str:
        return "PerfectMockAdapter"