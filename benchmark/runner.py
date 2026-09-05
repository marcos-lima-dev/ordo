import json
import jsonschema
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from .evaluator import Evaluator
from .metrics import MetricsCalculator

class BenchmarkRunner:
    def __init__(self, candidate, baseline_commit="5702f2b4af59560b40bae4ec8c6666b3f16e562a"):
        self.candidate = candidate
        self.baseline_commit = baseline_commit
        self.schema = self._load_schema()
        self.golden = self._load_golden()
        self.evaluator = Evaluator()

    def _load_schema(self):
        schema_path = Path("contracts/semantic_interpreter_v1_1_2.schema.json")
        with open(schema_path) as f:
            return json.load(f)

    def _load_golden(self):
        golden_path = Path("tests/golden_dataset.jsonl")
        dataset = []
        with open(golden_path) as f:
            for line in f:
                if line.strip():
                    dataset.append(json.loads(line))
        return dataset

    def run(self) -> Dict[str, Any]:
        results = []

        for case in self.golden:
            test_id = case["id"]
            input_msg = case["input"]
            expected = case["expected"]

            # Inicializa resultado
            result = {
                "test_id": test_id,
                "input": input_msg,
                "expected": expected,
                "schema_valid": False,
                "candidate_error": False,
                "error_message": None,
                "prediction": None,
                "evaluation": None,
            }

            # Executa candidato
            try:
                prediction = self.candidate.predict(input_msg)
                result["prediction"] = prediction
            except Exception as e:
                result["candidate_error"] = True
                result["error_message"] = str(e)
                results.append(result)
                continue

            # Valida schema
            try:
                jsonschema.validate(instance=prediction, schema=self.schema)
                result["schema_valid"] = True
            except jsonschema.ValidationError as e:
                result["schema_valid"] = False
                result["error_message"] = f"Schema validation error: {e.message}"

            # Avalia
            eval_result = self.evaluator.evaluate(expected, prediction)
            result["evaluation"] = eval_result

            results.append(result)

        # Métricas
        metrics = MetricsCalculator(results).compute()

        # Relatório
        report = {
            "metadata": {
                "candidate": self.candidate.name,
                "baseline_version": "v0",
                "baseline_commit": self.baseline_commit,
                "benchmark_version": "1.0",
                "timestamp": datetime.now().isoformat(),
            },
            "summary": {
                "total_cases": len(self.golden),
                "completed_cases": metrics["completed_cases"],
                "candidate_errors": metrics["candidate_errors"],
                "schema_valid_rate": metrics["schema_valid_rate"],
                "exact_case_match_rate": metrics["exact_case_match_rate"],
                "unsafe_resolution_count": metrics["unsafe_resolution_count"],
            },
            "field_accuracy": metrics["field_accuracy"],
            "unsafe_resolutions": self._extract_unsafe(results),
            "cases": results,
        }

        return report

    def _extract_unsafe(self, results):
        unsafe_list = []
        for r in results:
            eval_data = r.get("evaluation")
            if eval_data is None:
                continue
            if eval_data.get("_unsafe", False):
                unsafe_list.append({
                    "test_id": r["test_id"],
                    "input": r["input"],
                    "expected_status": r["expected"].get("product_resolution_status"),
                    "predicted_status": r["prediction"].get("product_resolution_status") if r["prediction"] else None,
                    "expected_candidates": r["expected"].get("catalog_candidates", []),
                    "predicted_candidates": r["prediction"].get("catalog_candidates", []) if r["prediction"] else [],
                })
        return unsafe_list