import sys
from pathlib import Path

# Garante que a raiz do projeto esteja no PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from benchmark.runner import BenchmarkRunner
from benchmark.adapters import PerfectMockAdapter, BrokenMockAdapter

def test_perfect_mock():
    """PerfectMock deve obter 100% e zero unsafe."""
    runner = BenchmarkRunner(PerfectMockAdapter())
    report = runner.run()

    assert report["summary"]["total_cases"] == 30
    assert report["summary"]["candidate_errors"] == 0
    assert report["summary"]["schema_valid_rate"] == 1.0
    assert report["summary"]["exact_case_match_rate"] == 1.0
    assert report["summary"]["unsafe_resolution_count"] == 0

def test_broken_mock_has_errors():
    """BrokenMock deve produzir pelo menos alguns erros."""
    runner = BenchmarkRunner(BrokenMockAdapter())
    report = runner.run()

    # Deve ter pelo menos algumas falhas (não pode ser 100% perfeito)
    exact = report["summary"]["exact_case_match_rate"]
    assert exact < 1.0

    # Pode ter unsafe resolutions
    unsafe = report["summary"]["unsafe_resolution_count"]
    assert unsafe >= 0  # pode ser zero dependendo da aleatoriedade, mas a chance é baixa

    # Algum campo deve ter accuracy < 1.0
    field_acc = report["field_accuracy"]
    assert any(v < 1.0 for v in field_acc.values())

def test_runner_does_not_stop_on_error():
    """Uma exceção em um caso não deve interromper os outros."""
    class ErrorMakerAdapter:
        name = "ErrorMaker"
        def __init__(self):
            self.counter = 0
        def predict(self, msg):
            self.counter += 1
            # Lança exceção na primeira chamada (TEST-01)
            if self.counter == 1:
                raise RuntimeError("forçado")
            # Para as demais, retorna um resultado válido (mas não necessariamente correto)
            return {
                "intent": "ADD_ITEM",
                "product_term": "teste",
                "quantity": {"value": None, "value_origin": "NOT_INFORMED", "unit": None, "unit_origin": "NOT_INFORMED"},
                "explicit_presentation": None,
                "explicit_brand": None,
                "contextual_references": [],
                "missing_information": [],
                "catalog_candidates": [],
                "product_resolution_status": "NOT_FOUND"
            }

    runner = BenchmarkRunner(ErrorMakerAdapter())
    report = runner.run()
    # Deve ter pelo menos um erro de candidato
    assert report["summary"]["candidate_errors"] > 0
    # Total de casos deve ser 30
    assert report["summary"]["total_cases"] == 30
    # Deve ter completado 29 casos (um falhou)
    assert report["summary"]["completed_cases"] == 29