from collections import defaultdict
from typing import List, Dict, Any

class MetricsCalculator:
    def __init__(self, results: List[Dict[str, Any]]):
        self.results = results
        self.total = len(results)

    def compute(self) -> Dict[str, Any]:
        # Infraestrutura
        schema_valid_count = sum(1 for r in self.results if r.get("schema_valid", False))
        candidate_errors = sum(1 for r in self.results if r.get("candidate_error", False))
        completed = self.total - candidate_errors

        # Exact case match (todos os campos + schema válido)
        exact_matches = sum(1 for r in self.results if r.get("schema_valid", False) and r.get("evaluation", {}).get("_all_pass", False))

        # Field accuracy
        field_accuracy = defaultdict(int)
        field_total = defaultdict(int)

        for r in self.results:
            if r.get("candidate_error"):
                continue
            eval_data = r.get("evaluation", {})
            for key, value in eval_data.items():
                if key.startswith("_"):
                    continue
                field_total[key] += 1
                if value:
                    field_accuracy[key] += 1

        field_rates = {k: field_accuracy[k] / field_total[k] if field_total[k] > 0 else 0.0 for k in field_total}

        # Unsafe resolutions - verifica se evaluation existe antes de acessar
        unsafe_count = sum(1 for r in self.results if r.get("evaluation") and r["evaluation"].get("_unsafe", False))

        return {
            "total_cases": self.total,
            "completed_cases": completed,
            "candidate_errors": candidate_errors,
            "schema_valid_rate": schema_valid_count / self.total if self.total else 0.0,
            "exact_case_match_rate": exact_matches / self.total if self.total else 0.0,
            "field_accuracy": field_rates,
            "unsafe_resolution_count": unsafe_count,
        }