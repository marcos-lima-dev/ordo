import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json

from order.state import OrderState
from order.engine import OrderEngine
from order.execution import execute_resolution
from pipeline.resolution_pipeline import resolve_operation


def load_conversations():
    path = Path("datasets/holdout_conversations.jsonl")
    cases = []
    with open(path) as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))
    return cases


def main():
    print("Carregando cenários conversacionais...")
    scenarios = load_conversations()
    print(f"Total: {len(scenarios)} cenários")

    engine = OrderEngine()

    results = []
    total_turns = 0
    correct_turns = 0
    correct_final_states = 0

    for scenario in scenarios:
        state = OrderState()
        scenario_id = scenario["id"]
        turns = scenario["turns"]
        print(f"\n--- {scenario_id} ({len(turns)} turnos) ---")

        turn_results = []
        for i, turn in enumerate(turns):
            msg = turn["message"]
            expected_intent = turn.get("expected_intent")

            # Canonical path: pipeline resolution + canonical execution.
            result = resolve_operation(msg, state)
            state, events = execute_resolution(state, result, engine)

            resolved_type = None
            if result.outcome.value == "OPERATION" and isinstance(result.operation, dict):
                resolved_type = result.operation.get("type")

            match = (resolved_type == expected_intent)
            if match:
                correct_turns += 1
            total_turns += 1

            turn_results.append({
                "turn": i + 1,
                "message": msg,
                "expected_intent": expected_intent,
                "resolved_operation_type": resolved_type,
                "resolution_result": {
                    "outcome": result.outcome.value,
                    "operation": result.operation,
                    "reason_code": result.reason_code,
                },
                "events": events,
                "match": match,
                "state_after": state.to_dict(),
            })

            print(f"  Turno {i+1}: {msg}")
            print(f"    Esperado: {expected_intent} | Resolvido: {resolved_type} {'✅' if match else '❌'}")
            print(f"    Outcome: {result.outcome.value} | Events: {events}")

        final_ok = False
        if state.status == "CONFIRMED":
            print("  ✅ Pedido confirmado corretamente.")
            final_ok = True
        elif state.status == "CANCELLED":
            print("  ✅ Pedido cancelado.")
            final_ok = True
        elif len(state.items) == 0:
            print("  ⚠️ Estado final vazio.")
        else:
            print(f"  ⚠️ Pedido ainda em aberto com {len(state.items)} itens.")

        if final_ok:
            correct_final_states += 1

        results.append({
            "scenario_id": scenario_id,
            "turns": turn_results,
            "final_state": state.to_dict(),
            "final_ok": final_ok,
        })

    print("\n=== RESUMO CONVERSACIONAL (Order Engine) ===")
    print(f"Turnos totais: {total_turns}")
    print(f"Intenções corretas por turno: {correct_turns}/{total_turns} ({correct_turns/total_turns*100:.1f}%)")
    print(f"Cenários com estado final correto: {correct_final_states}/{len(scenarios)}")

    output_path = Path("reports/holdout_conversational_results_v3.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_scenarios": len(scenarios),
            "total_turns": total_turns,
            "correct_turns": correct_turns,
            "turn_accuracy": correct_turns / total_turns if total_turns else 0,
            "correct_final_states": correct_final_states,
            "scenarios": results,
        }, f, indent=2, ensure_ascii=False)
    print(f"\nRelatório salvo em {output_path}")


if __name__ == "__main__":
    main()