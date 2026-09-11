import random
from .base import CandidateAdapter, register_adapter
from .perfect_mock import PerfectMockAdapter

@register_adapter("broken")
class BrokenMockAdapter(CandidateAdapter):
    def __init__(self):
        self._perfect = PerfectMockAdapter()

    def predict(self, message: str) -> dict:
        perfect = self._perfect.predict(message)
        errors = [
            self._wrong_intent,
            self._wrong_product_term,
            self._wrong_quantity_value,
            self._wrong_quantity_unit,
            self._wrong_quantity_origin,
            self._wrong_unit_origin,
            self._wrong_presentation,
            self._wrong_brand,
            self._wrong_contextual_references,
            self._wrong_missing_info,
            self._wrong_candidates,
            self._wrong_resolution_status,
            self._unsafe_resolution,
            self._schema_violation,
        ]
        error_func = random.choice(errors)
        return error_func(perfect)

    def _wrong_intent(self, perfect):
        perfect["intent"] = "UNKNOWN" if perfect["intent"] != "UNKNOWN" else "ADD_ITEM"
        return perfect

    def _wrong_product_term(self, perfect):
        perfect["product_term"] = "produto errado" if perfect["product_term"] else "produto errado"
        return perfect

    def _wrong_quantity_value(self, perfect):
        if perfect["quantity"]["value"] is not None:
            perfect["quantity"]["value"] += 1.0
        return perfect

    def _wrong_quantity_origin(self, perfect):
        origins = ["EXPLICIT", "INFERRED", "NOT_INFORMED"]
        current = perfect["quantity"]["value_origin"]
        others = [o for o in origins if o != current]
        perfect["quantity"]["value_origin"] = random.choice(others)
        return perfect

    def _wrong_quantity_unit(self, perfect):
        if perfect["quantity"]["unit"] is not None:
            perfect["quantity"]["unit"] = "unidade_errada"
        return perfect

    def _wrong_unit_origin(self, perfect):
        origins = ["EXPLICIT", "INFERRED", "NOT_INFORMED"]
        current = perfect["quantity"]["unit_origin"]
        others = [o for o in origins if o != current]
        perfect["quantity"]["unit_origin"] = random.choice(others)
        return perfect

    def _wrong_presentation(self, perfect):
        perfect["explicit_presentation"] = "apresentacao_errada" if perfect["explicit_presentation"] is None else None
        return perfect

    def _wrong_brand(self, perfect):
        perfect["explicit_brand"] = "marca_errada" if perfect["explicit_brand"] is None else None
        return perfect

    def _wrong_contextual_references(self, perfect):
        perfect["contextual_references"] = ["erro"]
        return perfect

    def _wrong_missing_info(self, perfect):
        perfect["missing_information"] = ["erro"]
        return perfect

    def _wrong_candidates(self, perfect):
        perfect["catalog_candidates"] = ["CQ-999"]
        return perfect

    def _wrong_resolution_status(self, perfect):
        statuses = ["EXACT_MATCH", "HIGH_CONFIDENCE", "AMBIGUOUS", "NOT_FOUND"]
        current = perfect["product_resolution_status"]
        others = [s for s in statuses if s != current]
        perfect["product_resolution_status"] = random.choice(others)
        return perfect

    def _unsafe_resolution(self, perfect):
        if perfect["product_resolution_status"] == "AMBIGUOUS":
            perfect["product_resolution_status"] = random.choice(["EXACT_MATCH", "HIGH_CONFIDENCE"])
        return perfect

    def _schema_violation(self, perfect):
        if "intent" in perfect:
            del perfect["intent"]
        return perfect

    @property
    def name(self) -> str:
        return "BrokenMockAdapter"