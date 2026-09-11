import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from order.state import OrderState
from pipeline.hybrid_v2 import HybridPipelineV2
from benchmark.adapters import DeterministicAdapter, TucanoAdapter

def load_conversational_cases():
    path = Path("datasets/development/conversational_cases.json")
    with open(path) as f:
        return json.load(f)

def evaluate_conversation(adapter, scenario):
    state = OrderState()
    results = []
    print(f"  Avaliando cenário {scenario['id']}...")
    for i, turn in enumerate(scenario["turns"]):
        msg = turn["message"]
        print(f"    Turno {i+1}: {msg}")
        try:
            if hasattr(adapter, "process"):
                output = adapter.process(msg, state)
                interpretation = output["interpretation"]
                new_state_dict = output["state"]
            else:
                interpretation = adapter.predict(msg)
                new_state_dict = state.to_dict()
        except Exception as e:
            print(f"      Erro no turno {i+1}: {e}")
            interpretation = {"intent": "ERROR", "product_term": "ERROR"}
            new_state_dict = state.to_dict()

        results.append({
            "message": msg,
            "expected_intent": turn.get("expected_intent"),
            "predicted_intent": interpretation.get("intent"),
            "expected_state": turn.get("expected_state"),
            "predicted_state": new_state_dict,
            "match": interpretation.get("intent") == turn.get("expected_intent")
        })
    return results

def main():
    scenarios = load_conversational_cases()
    print(f"Carregados {len(scenarios)} cenários conversacionais")

    adapters = {
        "Deterministic": DeterministicAdapter(),
        "Tucano-0.5B": TucanoAdapter(model_size="0.5B"),
        "Hybrid-V2": HybridPipelineV2()
    }

    for name, adapter in adapters.items():
        print(f"\nExecutando {name}...")
        scenario_results = []
        for scenario in scenarios:
            try:
                results = evaluate_conversation(adapter, scenario)
                matches = sum(1 for r in results if r["match"])
                scenario_results.append({
                    "scenario_id": scenario["id"],
                    "matches": matches,
                    "total": len(results),
                    "details": results
                })
            except Exception as e:
                print(f"  Erro no cenário {scenario['id']}: {e}")
                scenario_results.append({
                    "scenario_id": scenario["id"],
                    "error": str(e),
                    "matches": 0,
                    "total": len(scenario["turns"]),
                    "details": []
                })
        output_path = Path(f"reports/conversational_{name.replace('-', '_')}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(scenario_results, f, indent=2, ensure_ascii=False)
        print(f"  Resultados salvos em {output_path}")

if __name__ == "__main__":
    main()