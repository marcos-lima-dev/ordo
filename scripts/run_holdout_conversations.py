import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from collections import defaultdict
from benchmark.adapters import ModularAdapter
from order.state import OrderState, OrderItem
from order.target import TargetType
from pipeline.reference_resolver import ReferenceResolver
from order.resolution_context import ResolutionContext
from order.catalog_retriever import CatalogRetriever

def load_conversations(path="datasets/holdout_conversations.jsonl"):
    cases = []
    with open(path) as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))
    return cases

def get_target_and_constraints(state: OrderState, message: str, resolver: ReferenceResolver):
    """
    Usa o ReferenceResolver para determinar o alvo e extrair constraints.
    Retorna: target, brand_constraint, presentation_constraint, product_term (se disponível)
    """
    context = ResolutionContext.from_order_state(state)
    target = resolver.resolve(message, state, context)
    
    brand_constraint = target.brand_constraint if target.type in [TargetType.PENDING_ITEM, TargetType.EXISTING_ITEM] else None
    presentation_constraint = target.presentation_constraint if target.type in [TargetType.PENDING_ITEM, TargetType.EXISTING_ITEM] else None
    
    # Se for EXPLICIT_PRODUCT, tentamos extrair produto da mensagem (via GLiNER)
    product_term = None
    if target.type == TargetType.EXPLICIT_PRODUCT:
        product_term = target.product_term
    elif target.type in [TargetType.PENDING_ITEM, TargetType.EXISTING_ITEM]:
        # Para itens existentes ou pendentes, usamos o produto do estado
        if target.item_id:
            # Busca o item no estado
            for item in state.items:
                if item.product_term == target.item_id:
                    product_term = item.product_term
                    break
        elif state.pending_resolution:
            product_term = state.pending_resolution.product_term
    
    return target, brand_constraint, presentation_constraint, product_term

def apply_interpretation(state: OrderState, interpretation: dict, turn: dict, resolver: ReferenceResolver):
    """
    Aplica a interpretação ao estado, usando ReferenceResolver para melhorar a resolução.
    """
    intent = interpretation.get("intent")
    product_raw = interpretation.get("product_term")
    quantity = interpretation.get("quantity", {}).get("value")
    unit = interpretation.get("quantity", {}).get("unit")
    brand = interpretation.get("explicit_brand")
    presentation = interpretation.get("explicit_presentation")
    status = interpretation.get("product_resolution_status")
    candidates = interpretation.get("catalog_candidates", [])

    # Usa ReferenceResolver para obter target e constraints
    target, brand_constraint, presentation_constraint, product_term = get_target_and_constraints(state, turn["message"], resolver)

    # Se o target for PENDING_ITEM ou EXISTING_ITEM, aplica constraints para refinar candidatos
    if target.type in [TargetType.PENDING_ITEM, TargetType.EXISTING_ITEM]:
        if brand_constraint and not brand:
            brand = brand_constraint
        if presentation_constraint and not presentation:
            presentation = presentation_constraint
        if product_term and not product_raw:
            product_raw = product_term

    # Verifica se há ambiguidade
    needs_clarification = (status in ["AMBIGUOUS", "NOT_FOUND"]) if status else False

    # Cria item se for ADD_ITEM
    if intent == "ADD_ITEM" and product_raw:
        item = OrderItem(
            product_term=product_raw,
            quantity=quantity,
            unit=unit,
            brand=brand,
            presentation=presentation,
            resolved=(status == "EXACT_MATCH"),
            needs_clarification=needs_clarification,
            clarification_questions=interpretation.get("missing_information", []) if needs_clarification else []
        )
        state.add_item(item)
        return {"action": "ADD_ITEM", "item": product_raw}

    # CHANGE_QUANTITY: identifica o item alvo
    elif intent == "CHANGE_QUANTITY":
        if quantity is None:
            return {"action": "CHANGE_QUANTITY", "item": None, "error": "NO_QUANTITY"}
        
        target_item = None
        if target.type == TargetType.EXISTING_ITEM and target.item_id:
            # Busca o item pelo product_term
            for item in state.items:
                if item.product_term == target.item_id:
                    target_item = item
                    break
        elif target.type == TargetType.PENDING_ITEM and state.pending_resolution:
            target_item = state.pending_resolution
        elif state.items:
            # Fallback: usa o último item (com cautela)
            target_item = state.items[-1]
        
        if target_item:
            old_qty = target_item.quantity
            target_item.quantity = quantity
            return {"action": "CHANGE_QUANTITY", "item": target_item.product_term, "old": old_qty, "new": quantity}
        else:
            return {"action": "CHANGE_QUANTITY", "item": None, "error": "NO_TARGET"}

    # REMOVE_ITEM: remove o item alvo
    elif intent == "REMOVE_ITEM":
        if target.type == TargetType.EXISTING_ITEM and target.item_id:
            for i, item in enumerate(state.items):
                if item.product_term == target.item_id:
                    state.items.pop(i)
                    return {"action": "REMOVE_ITEM", "item": target.item_id}
        elif state.items:
            # Fallback: remove o último item
            removed = state.items[-1].product_term
            state.items.pop()
            return {"action": "REMOVE_ITEM", "item": removed}
        return {"action": "REMOVE_ITEM", "item": None}

    # CONFIRM_ORDER
    elif intent == "CONFIRM_ORDER":
        if state.pending_resolution is None and not any(item.needs_clarification for item in state.items):
            state.status = "CONFIRMED"
            return {"action": "CONFIRM_ORDER", "success": True}
        else:
            state.status = "NEEDS_CLARIFICATION"
            return {"action": "CONFIRM_ORDER", "success": False, "reason": "PENDENCIAS"}

    # CANCEL_ORDER
    elif intent == "CANCEL_ORDER":
        state.status = "CANCELED"
        state.items = []
        return {"action": "CANCEL_ORDER", "success": True}

    return {"action": "UNKNOWN"}

def main():
    print("Carregando cenários conversacionais...")
    scenarios = load_conversations()
    print(f"Total: {len(scenarios)} cenários")

    adapter = ModularAdapter()
    resolver = ReferenceResolver()
    retriever = CatalogRetriever()

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

            # Interpreta a mensagem com o ModularAdapter
            interpretation = adapter.predict(msg)
            pred_intent = interpretation.get("intent")

            # Aplica a interpretação ao estado (usando ReferenceResolver)
            action_info = apply_interpretation(state, interpretation, turn, resolver)

            # Avalia se a intenção está correta
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
                "match": match,
                "state_after": state.to_dict()
            })

            print(f"  Turno {i+1}: {msg}")
            print(f"    Esperado: {expected_intent} | Predito: {pred_intent} {'✅' if match else '❌'}")
            print(f"    Ação: {action_info}")

        # Avalia estado final (simplificado)
        final_ok = False
        if state.status == "CONFIRMED":
            print("  ✅ Pedido confirmado corretamente.")
            final_ok = True
        elif state.status == "CANCELED":
            print("  ✅ Pedido cancelado.")
            final_ok = True
        elif len(state.items) > 0:
            print(f"  ⚠️ Pedido ainda em aberto com {len(state.items)} itens.")
        else:
            print("  ⚠️ Estado final vazio ou indefinido.")

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

    # Salva relatório
    output_path = Path("reports/holdout_conversational_results.json")
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