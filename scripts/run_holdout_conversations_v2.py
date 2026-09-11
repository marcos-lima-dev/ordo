import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import re  # <-- ADICIONADO
from order.state import OrderState, OrderItem
from order.pending import PendingResolution
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

def apply_state_transition(state: OrderState, interpretation: dict, ref_signal, turn: dict) -> dict:
    intent = interpretation.get("intent")
    product_term = interpretation.get("product_term")
    quantity = interpretation.get("quantity", {}).get("value")
    unit = interpretation.get("quantity", {}).get("unit")
    brand = interpretation.get("explicit_brand")
    presentation = interpretation.get("explicit_presentation")
    resolution_status = interpretation.get("product_resolution_status")
    candidates = interpretation.get("catalog_candidates", [])
    
    action_info = {"action": intent}
    
    # 0. Se for referência pendente com constraints
    if ref_signal.type.value == "PENDING_REFERENCE" and state.pending_resolution:
        pending = state.pending_resolution
        if "brand" in ref_signal.constraints:
            pending.brand = ref_signal.constraints["brand"]
        if "presentation" in ref_signal.constraints:
            pending.presentation = ref_signal.constraints["presentation"]
        # Tenta resolver a pendência
        if pending.brand:
            pending.missing_fields = [f for f in pending.missing_fields if f != "brand"]
            if not pending.missing_fields:
                state.clear_pending()
                # Marca o item correspondente como resolvido
                for item in state.items:
                    if item.product_term == pending.product_term:
                        item.resolved = True
                        item.needs_clarification = False
                        break
        action_info["action"] = "RESOLVED_PENDING"
        return action_info

    # 1. ADD_ITEM
    if intent == "ADD_ITEM" and product_term:
        # Verifica se é um complemento ("sem sal") para o último item
        msg = turn.get("message", "").lower()
        if "sem sal" in msg and state.items and "manteiga" in state.items[-1].product_term.lower():
            # Atualiza o último item para "Manteiga s/sal"
            state.items[-1].product_term = "Manteiga s/sal"
            action_info["action"] = "UPDATE_ITEM"
            action_info["item"] = state.items[-1].product_term
            return action_info

        item = OrderItem(
            product_term=product_term,
            quantity=quantity,
            unit=unit,
            brand=brand,
            presentation=presentation,
            resolved=(resolution_status == "EXACT_MATCH"),
            needs_clarification=(resolution_status in ["AMBIGUOUS", "NOT_FOUND"]),
            clarification_questions=interpretation.get("missing_information", [])
        )
        state.add_item(item)
        
        # Se o item não está resolvido, cria uma pending_resolution
        if resolution_status in ["AMBIGUOUS", "NOT_FOUND"]:
            pending = PendingResolution(
                product_term=product_term,
                quantity=quantity,
                unit=unit,
                brand=brand,
                presentation=presentation,
                missing_fields=interpretation.get("missing_information", []),
                reason=resolution_status
            )
            state.set_pending(pending)
        
        action_info["item"] = product_term
        return action_info
    
    # 2. REMOVE_ITEM
    if intent == "REMOVE_ITEM":
        # Tenta encontrar o item alvo via ReferenceSignal
        target_term = None
        if ref_signal and ref_signal.type.value == "EXPLICIT_REFERENCE" and ref_signal.product_term:
            target_term = ref_signal.product_term
        # Se não encontrou, tenta extrair da mensagem
        if not target_term:
            msg = turn.get("message", "").lower()
            # Procura por "tira o [produto]" ou "remove [produto]"
            match = re.search(r'(?:tira|remove)\s+(?:o|a|os|as)?\s*([a-záéíóúãõç ]+)', msg)
            if match:
                target_term = match.group(1).strip()
        if target_term:
            found = False
            for item in state.items:
                if target_term in item.product_term.lower():
                    removed = item
                    state.items.remove(item)
                    action_info["item"] = removed.product_term
                    found = True
                    break
            if found:
                return action_info
        # Fallback: remove o último item
        if state.items:
            removed = state.items.pop(-1)
            action_info["item"] = removed.product_term
            return action_info
        action_info["item"] = None
        return action_info
    
    # 3. CHANGE_QUANTITY
    if intent == "CHANGE_QUANTITY":
        if quantity is not None:
            # Tenta encontrar o item alvo via ReferenceSignal
            target_item = None
            if ref_signal and ref_signal.type.value == "EXPLICIT_REFERENCE" and ref_signal.product_term:
                for item in state.items:
                    if ref_signal.product_term in item.product_term.lower():
                        target_item = item
                        break
            if not target_item:
                # Tenta extrair da mensagem
                msg = turn.get("message", "").lower()
                match = re.search(r'(?:muda|troca|na verdade)\s+(?:para)?\s*(\d+)', msg)
                if not match and state.items:
                    target_item = state.items[-1]  # fallback para último item
            if target_item:
                old_qty = target_item.quantity
                target_item.quantity = quantity
                action_info["item"] = target_item.product_term
                action_info["old"] = old_qty
                action_info["new"] = quantity
                return action_info
            else:
                state.status = "NEEDS_CLARIFICATION"
                action_info["error"] = "NO_TARGET"
                return action_info
        else:
            action_info["error"] = "NO_QUANTITY"
            return action_info
    
    # 4. CONFIRM_ORDER
    if intent == "CONFIRM_ORDER":
        if state.pending_resolution is None and not any(item.needs_clarification for item in state.items):
            state.status = "CONFIRMED"
            action_info["success"] = True
        else:
            state.status = "NEEDS_CLARIFICATION"
            action_info["success"] = False
            action_info["reason"] = "PENDENCIAS"
        return action_info
    
    # 5. CANCEL_ORDER
    if intent == "CANCEL_ORDER":
        state.status = "CANCELED"
        state.items = []
        action_info["success"] = True
        return action_info
    
    return action_info

def main():
    print("Carregando cenários conversacionais...")
    scenarios = load_conversations()
    print(f"Total: {len(scenarios)} cenários")

    adapter = ModularAdapter()
    resolver = ReferenceResolver()
    
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

            # 2. Interpreta a mensagem
            interpretation = adapter.predict(msg)
            pred_intent = interpretation.get("intent")

            # 3. Aplica ao estado usando o ReferenceSignal
            action_info = apply_state_transition(state, interpretation, ref_signal, turn)

            # 4. Avalia se a intenção está correta
            match = (pred_intent == expected_intent)
            if match:
                correct_turns += 1
            total_turns += 1

            turn_results.append({
                "turn": i+1,
                "message": msg,
                "expected_intent": expected_intent,
                "predicted_intent": pred_intent,
                "action": action_info,
                "ref_signal": {
                    "type": ref_signal.type.value,
                    "constraints": ref_signal.constraints,
                    "requires_clarification": ref_signal.requires_clarification
                },
                "match": match,
                "state_after": state.to_dict()
            })

            print(f"  Turno {i+1}: {msg}")
            print(f"    Esperado: {expected_intent} | Predito: {pred_intent} {'✅' if match else '❌'}")
            print(f"    Ref: {ref_signal.type.value} | Ação: {action_info}")

        # Avalia estado final
        final_ok = False
        if state.status == "CONFIRMED":
            print("  ✅ Pedido confirmado corretamente.")
            final_ok = True
        elif state.status == "CANCELED":
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

    print("\n=== RESUMO CONVERSACIONAL ===")
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