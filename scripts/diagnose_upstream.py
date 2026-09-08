import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from typing import Dict, List, Any, Optional
from collections import defaultdict

from order.state import OrderState, OrderItem
from order.resolved_operation import ResolvedOperation, OperationType
from benchmark.adapters.modular import ModularAdapter
from pipeline.reference_resolver import ReferenceResolver
from order.catalog_retriever import CatalogRetriever
from order.product_resolver import ProductResolver

# =============================================
# Carregamento dos datasets
# =============================================

def load_dev_set():
    path = Path("datasets/resolved_operation_dev.jsonl")
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]

def build_state(state_data: Dict[str, Any]) -> OrderState:
    state = OrderState()
    for item_data in state_data.get("items", []):
        item = OrderItem(
            product_term=item_data.get("product_term", ""),
            product_id=item_data.get("product_id"),
            quantity=item_data.get("quantity"),
            unit=item_data.get("unit"),
            resolved=item_data.get("resolved", False),
            needs_clarification=item_data.get("needs_clarification", False)
        )
        state.add_item(item)
    state.status = state_data.get("status", "OPEN")
    return state

# =============================================
# Pipeline upstream (diagnóstico)
# =============================================

_adapter = None
_resolver = None
_catalog_retriever = None
_product_resolver = None

def get_adapter():
    global _adapter
    if _adapter is None:
        _adapter = ModularAdapter()
    return _adapter

def get_resolver():
    global _resolver
    if _resolver is None:
        _resolver = ReferenceResolver()
    return _resolver

def get_catalog_retriever():
    global _catalog_retriever
    if _catalog_retriever is None:
        _catalog_retriever = CatalogRetriever()
    return _catalog_retriever

def get_product_resolver():
    global _product_resolver
    if _product_resolver is None:
        _product_resolver = ProductResolver()
    return _product_resolver

def diagnose_case(case: Dict[str, Any]) -> Dict[str, Any]:
    state_before = build_state(case["state_before"])
    message = case["message"]
    expected = case["expected"]
    expected_op = expected.get("operation")
    expected_outcome = expected.get("outcome")

    adapter = get_adapter()
    resolver = get_resolver()
    catalog_retriever = get_catalog_retriever()
    product_resolver = get_product_resolver()

    # 1. Reference Resolution
    ref_signal = resolver.resolve(message, state_before)

    # 2. Interpretação (NLP)
    interpretation = adapter.predict(message)
    intent = interpretation.get("intent")
    product_term = interpretation.get("product_term")
    brand = interpretation.get("explicit_brand")
    presentation = interpretation.get("explicit_presentation")
    quantity = interpretation.get("quantity", {}).get("value")
    unit = interpretation.get("quantity", {}).get("unit")
    candidates_raw = interpretation.get("catalog_candidates", [])
    resolution_status = interpretation.get("product_resolution_status")

    # 3. Catalog retrieval (para verificar candidatos)
    catalog_candidates = catalog_retriever.retrieve_with_constraints(
        message,
        brand=brand,
        presentation=presentation
    )

    # 4. Product resolution (para verificar status)
    # Usando o mesmo resolver do adaptador
    product_resolution_status = product_resolver.resolve(
        catalog_candidates,
        product_term=product_term,
        brand=brand
    )

    # 5. Target Resolution (replicar a lógica do resolve_operation)
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
        op_type = OperationType.UNKNOWN

    # Target candidates (itens existentes no estado que podem ser alvo)
    target_candidates = []
    target_evidence = None
    target_source = "UNKNOWN"
    target_selected_id = None

    # Verifica se há referência explícita a um item
    explicit_target = None
    if ref_signal and ref_signal.product_term:
        for item in state_before.items:
            if item.product_term == ref_signal.product_term:
                explicit_target = item.id
                target_source = "EXPLICIT_ITEM_REFERENCE"
                break
    if explicit_target:
        target_selected_id = explicit_target
        target_evidence = f"ref_signal.product_term: {ref_signal.product_term}"
    else:
        # Verifica se a mensagem menciona um produto existente
        if product_term:
            for item in state_before.items:
                if item.product_term == product_term:
                    target_selected_id = item.id
                    target_source = "PRODUCT_MENTION"
                    target_evidence = f"product_term: {product_term}"
                    break
        # Se ainda não encontrou, verifica PendingResolution
        if not target_selected_id and state_before.pending_resolution:
            pending = state_before.pending_resolution
            if pending.product_term:
                for item in state_before.items:
                    if item.product_term == pending.product_term:
                        target_selected_id = item.id
                        target_source = "PENDING_REFERENCE"
                        target_evidence = f"pending.product_term: {pending.product_term}"
                        break
        # Fallback: último item (se houver)
        if not target_selected_id and state_before.items:
            target_selected_id = state_before.items[-1].id
            target_source = "LAST_ITEM_FALLBACK"
            target_evidence = "no explicit target, using last item"

    # Target candidates (todos os itens do estado)
    target_candidates = [item.id for item in state_before.items]

    # 6. Safety outcome (simulado, pois não usamos o Order Engine aqui)
    safety_outcome = "NOT_APPLICABLE"
    unsafe = False

    # 7. Comparação com expected
    actual_op = ResolvedOperation(
        type=op_type,
        product_id=interpretation.get("catalog_candidates", [])[0] if interpretation.get("catalog_candidates") else None,
        product_term=product_term,
        target_item_id=target_selected_id,
        quantity_value=quantity,
        quantity_unit=unit,
        evidence=["interpretation"]
    )

    # Determina se a operação é válida (simples)
    is_valid = actual_op.is_valid()
    if is_valid and op_type != OperationType.UNKNOWN:
        outcome = "OPERATION"
    else:
        outcome = "NEEDS_CLARIFICATION"

    # Verifica se o outcome esperado é alcançado
    match_outcome = (outcome == expected_outcome)

    # Se o outcome for OPERATION, verifica se a operação coincide com expected
    match_operation = False
    if match_outcome and expected_op:
        exp_type = expected_op.get("type")
        if exp_type == actual_op.type.value:
            # Verifica campos obrigatórios (simplificado)
            required_fields = {
                "ADD_ITEM": ["product_id"],
                "REMOVE_ITEM": ["target_item_id"],
                "CHANGE_QUANTITY": ["target_item_id", "quantity_value"],
                "REPLACE_ITEM": ["target_item_id", "replacement_product_id"],
                "CONFIRM_ORDER": [],
                "CANCEL_ORDER": [],
            }
            fields = required_fields.get(exp_type, [])
            all_match = True
            for field in fields:
                exp_val = expected_op.get(field)
                act_val = getattr(actual_op, field, None)
                if exp_val != act_val:
                    all_match = False
                    break
            if all_match and exp_type in ["CHANGE_QUANTITY", "ADD_ITEM"]:
                if expected_op.get("quantity_value") != actual_op.quantity_value:
                    all_match = False
                if expected_op.get("quantity_unit") != actual_op.quantity_unit:
                    all_match = False
            if all_match:
                match_operation = True

    # Classifica a falha (se houver)
    root_cause = "NONE"
    downstream_outcome = "NOT_APPLICABLE"
    if not match_outcome or not match_operation:
        if not match_outcome and expected_outcome == "NEEDS_CLARIFICATION" and outcome == "OPERATION":
            root_cause = "RESOLVED_OPERATION_COMPOSITION_ERROR"  # ou TARGET_RESOLUTION_ERROR
            downstream_outcome = "WRONG_EXECUTION"
        elif not match_outcome and expected_outcome == "OPERATION" and outcome == "NEEDS_CLARIFICATION":
            root_cause = "INTENT_ERROR"  # ou ENTITY_ERROR
            downstream_outcome = "UNNECESSARY_CLARIFICATION"
        elif not match_operation:
            # Verifica se o problema é target
            if expected_op and expected_op.get("target_item_id") != actual_op.target_item_id:
                root_cause = "TARGET_RESOLUTION_ERROR"
                downstream_outcome = "WRONG_EXECUTION"
            elif expected_op and expected_op.get("product_id") != actual_op.product_id:
                root_cause = "PRODUCT_RESOLUTION_ERROR"
                downstream_outcome = "WRONG_EXECUTION"
            elif expected_op and expected_op.get("type") != actual_op.type.value:
                root_cause = "INTENT_ERROR"
                downstream_outcome = "WRONG_EXECUTION"
            else:
                root_cause = "OTHER"
                downstream_outcome = "NO_STATE_CHANGE"
    else:
        if expected_outcome == "OPERATION":
            downstream_outcome = "CORRECT_EXECUTION"
        else:
            downstream_outcome = "SAFE_CLARIFICATION"

    # 8. Monta o trace
    trace = {
        "case_id": case["id"],
        "message": message,
        "state_before": state_before.to_dict(),
        "expected": expected,
        "intent_signal": intent,
        "intent_source": "CLASSIFIER" if intent and intent in intent_map else "DETERMINISTIC_RULE",
        "entity_signals": {
            "product_term": product_term,
            "brand": brand,
            "presentation": presentation,
            "quantity": quantity,
            "unit": unit,
        },
        "reference_signal": {
            "type": ref_signal.type.value if ref_signal else "UNKNOWN",
            "constraints": ref_signal.constraints if ref_signal else {},
            "product_term": ref_signal.product_term if ref_signal else None,
            "requires_clarification": ref_signal.requires_clarification if ref_signal else False,
        },
        "catalog_candidates": catalog_candidates,
        "product_resolution_status": product_resolution_status,
        "target_candidates": target_candidates,
        "target_selected": target_selected_id,
        "target_evidence": target_evidence,
        "target_source": target_source,
        "resolution_outcome": outcome,
        "actual_operation": actual_op.__dict__,
        "match_outcome": match_outcome,
        "match_operation": match_operation,
        "overall_match": match_outcome and match_operation,
        "root_cause": root_cause,
        "downstream_outcome": downstream_outcome,
    }
    return trace

# =============================================
# Main
# =============================================

def main():
    dev_cases = load_dev_set()
    print(f"Diagnosticando {len(dev_cases)} casos do DEV...")

    traces = []
    for case in dev_cases:
        trace = diagnose_case(case)
        traces.append(trace)

    # Salva o relatório completo
    output_path = Path("reports/dev_diagnostic.json")
    with open(output_path, "w") as f:
        json.dump(traces, f, indent=2, ensure_ascii=False, default=str)
    print(f"Relatório salvo em {output_path}")

    # Exibe resumo no terminal
    total = len(traces)
    exact_matches = sum(1 for t in traces if t["overall_match"])
    print(f"\nTotal: {total}")
    print(f"Exact Matches: {exact_matches} ({exact_matches/total*100:.1f}%)")

    # Distribuição de target_source
    print("\nTarget Source Distribution:")
    target_sources = defaultdict(int)
    for t in traces:
        target_sources[t["target_source"]] += 1
    for source, count in sorted(target_sources.items()):
        print(f"  {source}: {count}")

    # Casos com LAST_ITEM_FALLBACK
    fallback_cases = [t for t in traces if t["target_source"] == "LAST_ITEM_FALLBACK"]
    if fallback_cases:
        print(f"\nLAST_ITEM_FALLBACK occurrences ({len(fallback_cases)}):")
        for t in fallback_cases:
            print(f"  {t['case_id']}: {t['message']} -> target: {t['target_selected']}")

    # Erros por causa raiz
    print("\nRoot Cause Distribution:")
    root_causes = defaultdict(int)
    for t in traces:
        if not t["overall_match"]:
            root_causes[t["root_cause"]] += 1
    for cause, count in sorted(root_causes.items()):
        print(f"  {cause}: {count}")

    # Casos de NEEDS_CLARIFICATION
    clarification_cases = [t for t in traces if t["expected"]["outcome"] == "NEEDS_CLARIFICATION"]
    if clarification_cases:
        print(f"\nNEEDS_CLARIFICATION cases ({len(clarification_cases)}):")
        for t in clarification_cases:
            actual_outcome = t["resolution_outcome"]
            match = t["match_outcome"]
            print(f"  {t['case_id']}: expected CLARIFICATION, got {actual_outcome} {'✅' if match else '❌'}")

if __name__ == "__main__":
    main()