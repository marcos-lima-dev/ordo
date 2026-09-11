import sys
from pathlib import Path

# Adiciona a raiz do projeto ao PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from benchmark.adapters import DeterministicAdapter, TucanoAdapter
from pipeline.hybrid_v2 import HybridPipelineV2

def load_linguistic_cases():
    path = Path("datasets/development/linguistic_cases.json")
    with open(path) as f:
        return json.load(f)

def evaluate_adapter(adapter, cases):
    results = []
    for case in cases:
        msg = case["message"]
        expected = case["expected"]
        prediction = adapter.predict(msg)
        # Comparação simplificada: verifica intent e product_term
        match = (
            prediction.get("intent") == expected.get("intent") and
            prediction.get("product_term") == expected.get("product_term")
        )
        results.append({
            "id": case["id"],
            "message": msg,
            "expected": expected,
            "prediction": prediction,
            "match": match
        })
    return results

def main():
    cases = load_linguistic_cases()
    print(f"Carregados {len(cases)} casos linguísticos")

    adapters = {
        "Deterministic": DeterministicAdapter(),
        "Tucano-0.5B": TucanoAdapter(model_size="0.5B"),
        "Hybrid-V2": HybridPipelineV2()
    }

    for name, adapter in adapters.items():
        print(f"\nExecutando {name}...")
        results = evaluate_adapter(adapter, cases)
        matches = sum(1 for r in results if r["match"])
        print(f"  Acertos: {matches}/{len(cases)} ({matches/len(cases)*100:.1f}%)")
        # Salva resultado detalhado
        output_path = Path(f"reports/linguistic_{name.replace('-', '_')}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"  Detalhes salvos em {output_path}")

if __name__ == "__main__":
    main()