import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import re
from order.state import OrderState
from order.engine import OrderEngine
from order.resolved_operation import ResolvedOperation, OperationType
from benchmark.adapters.modular import ModularAdapter
from pipeline.reference_resolver import ReferenceResolver

def load_conversations():
    path = Path("datasets/holdout_conversations.jsonl")
    cases = []
    with open(path) as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))
    return cases

def resolve_operation(state: OrderState, interpretation: dict, ref_signal, turn: dict) -> ResolvedOperation:
    """
    Converte a interpretação em uma ResolvedOperation para o Order Engine.
    """
    intent = interpretation.get("intent")
    product_term = interpretation.get("product_term")
    quantity = interpretation.get("quantity", {}).get("value")
    unit = interpretation.get("quantity", {}).get("unit")
    brand = interpretation.get("explicit_brand")
    presentation = interpretation.get("explicit_presentation")
    candidates = interpretation.get("catalog_candidates", [])
    resolution_status = interpretation.get("product_resolution_status")
    
    # Mapeia intent para OperationType
    intent_map = {
        "ADD_ITEM": OperationType.ADD_ITEM,
        "REMOVE_ITEM": OperationType.REMOVE_ITEM,
        "CHANGE_QUANTITY": OperationType.CHANGE_QUANTITY,
        "REPLACE_ITEM": OperationType.REPLACE_ITEM,
        "CONFIRM_ORDER": OperationType.CONFIRM_ORDER,
        "CANCEL_ORDER": OperationType.CANCEL_ORDER,
    }
    
    op_type = intent_map.get(intent)
    if op_type is None:
        # Fallback: se não reconhecer, retorna uma operação vazia (será rejeitada)
        return ResolvedOperation(type=OperationType.UNKNOWN)
    
    # Identifica target_item_id
    target_id = None
    if ref_signal and ref_signal.item_id:
        target_id = ref_signal.item_id
    elif ref_signal and ref_signal.product_term:
        # Tenta encontrar o item pelo product_term
        for item in state.items:
            if item.product_term == ref_signal.product_term:
                target_id = item.id
                break
    
    # Se não encontrou via ref_signal, tenta extrair da mensagem
    if not target_id and product_term:
        for item in state.items:
            if item.product_term == product_term:
                target_id = item.id
                break
    
    # Para ADD_ITEM, se não houver product_id, usamos product_term
    product_id = None
    if candidates and len(candidates) == 1:
        product_id = candidates[0]
    
    # Constrói a operação
    return ResolvedOperation(
        type=op_type,
        product_id=product_id,
        product_term=product_term,
        target_item_id=target_id,
        quantity_value=quantity,
        quantity_unit=unit,
        source_message_id=turn.get("id"),
        evidence=["interpretation"]
    )

def main():
    print("Carregando cenários conversacionais...")
    scenarios = load_conversations()
    print(f"Total: {len(scenarios)} cenários")

    adapter = ModularAdapter()
    resolver = ReferenceResolver()
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

            # 1. Resolve referência
            ref_signal = resolver.resolve(msg, state)

            # 2. Interpreta a mensagem (NLP)
            interpretation = adapter.predict(msg)
            pred_intent = interpretation.get("intent")

            # 3. Cria ResolvedOperation
            op = resolve_operation(state, interpretation, ref_signal, turn)

            # 4. Aplica ao estado usando o Order Engine
            new_state, events = engine.apply(state, op)
            state = new_state  # atualiza estado

            # 5. Avalia se a intenção está correta
            match = (pred_intent == expected_intent)
            if match:
                correct_turns += 1
            total_turns += 1

            turn_results.append({
                "turn": i+1,
                "message": msg,
                "expected_intent": expected_intent,
                "predicted_intent": pred_intent,
                "operation": {
                    "type": op.type.value,
                    "product_id": op.product_id,
                    "target_item_id": op.target_item_id,
                    "quantity": op.quantity_value,
                },
                "events": events,
                "match": match,
                "state_after": state.to_dict()
            })

            print(f"  Turno {i+1}: {msg}")
            print(f"    Esperado: {expected_intent} | Predito: {pred_intent} {'✅' if match else '❌'}")
            print(f"    Op: {op.type.value} | Events: {events}")

        # Avalia estado final
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
            "final_ok": final_ok
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
            "turn_accuracy": correct_turns/total_turns if total_turns else 0,
            "correct_final_states": correct_final_states,
            "scenarios": results
        }, f, indent=2, ensure_ascii=False)
    print(f"\nRelatório salvo em {output_path}")

if __name__ == "__main__":
    main()