from typing import Dict, Any, List, Tuple

class Evaluator:
    """Compara prediction vs expected campo a campo."""

    def __init__(self):
        # Define campos que são conjuntos (ordem irrelevante)
        self._set_fields = [
            "contextual_references",
            "missing_information",
            "catalog_candidates"
        ]

    def evaluate(self, expected: Dict[str, Any], prediction: Dict[str, Any]) -> Dict[str, Any]:
        """Retorna dicionário com status de cada campo e unsafe flag."""
        results = {}

        # Campos top-level (exceto quantity que é objeto)
        top_fields = ["intent", "product_term", "explicit_presentation", "explicit_brand", "product_resolution_status"]
        for field in top_fields:
            results[field] = self._compare_scalar(expected.get(field), prediction.get(field))

        # Campos de quantity
        q_fields = ["value", "value_origin", "unit", "unit_origin"]
        for qf in q_fields:
            key = f"quantity.{qf}"
            exp_val = expected.get("quantity", {}).get(qf)
            pred_val = prediction.get("quantity", {}).get(qf)
            results[key] = self._compare_scalar(exp_val, pred_val)

        # Campos que são arrays (tratamento de conjunto)
        for field in self._set_fields:
            exp_set = set(expected.get(field, []))
            pred_set = set(prediction.get(field, []))
            results[field] = (exp_set == pred_set)

        # Sinaliza se todos os campos estão corretos
        all_pass = all(results.values())
        results["_all_pass"] = all_pass

        # Detecta unsafe resolution
        unsafe = False
        expected_res = expected.get("product_resolution_status")
        predicted_res = prediction.get("product_resolution_status")
        if expected_res == "AMBIGUOUS" and predicted_res in ["EXACT_MATCH", "HIGH_CONFIDENCE"]:
            unsafe = True
        results["_unsafe"] = unsafe

        return results

    def _compare_scalar(self, expected, predicted) -> bool:
        # Trata equivalência numérica (10 e 10.0)
        if isinstance(expected, (int, float)) and isinstance(predicted, (int, float)):
            return expected == predicted
        return expected == predicted