import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from typing import Dict, List, Any, Optional
from collections import defaultdict

from order.state import OrderState, OrderItem
from order.resolved_operation import ResolvedOperation, OperationType
from order.resolution_result import ResolutionResult, OutcomeType
from order.resolution_evaluator import evaluate_resolution
from order.target_resolver import TargetResolver, TargetStatus
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
_target_resolver = None

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

def get_target_resolver():
    global _target_resolver
    if _target_resolver is None:
        _target_resolver = TargetResolver()
    return _target_resolver

def diagnose_case(case: Dict[str, Any]) -> Dict[str, Any]:
    state_before = build_state(case["state_before"])
    message = case["message"]
    expected = case["expected"]

    adapter = get_adapter()
    resolver = get_resolver()
    catalog_retriever = get_catalog_retriever()
    product_resolver = get_product_resolver()
    target_resolver = get_target_resolver()

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

    # 3. Catalog retrieval
    catalog_candidates = catalog_retriever.retrieve_with_constraints(
        message, brand=brand, presentation=presentation
    )
    product_resolution_status = product_resolver.resolve(
        catalog_candidates, product_term=product_term, brand=brand
    )

    # 4. Target Resolution (com TargetResolver)
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

    target_result = None
    target_selected_id = None
    target_source = "NOT_APPLICABLE"
    target_evidence = None

    if op_type in [OperationType.REMOVE_ITEM, OperationType.CHANGE_QUANTITY, OperationType.REPLACE_ITEM]:
        target_result = target_resolver.resolve(
            message=message,
            state=state_before,
            reference_product_term=product_term,
            ref_signal=ref_signal,
        )
        target_selected_id = target_result.target_item_id
        target_source = target_result.source.value
        target_evidence = "; ".join(target_result.evidence)

    # 5. Monta a operação (mesma lógica do resolve_operation)
    product_id = None
    if catalog_candidates and len(catalog_candidates) == 1:
        product_id = catalog_candidates[0]

    if op_type in [OperationType.REMOVE_ITEM, OperationType.CHANGE_QUANTITY, OperationType.REPLACE_ITEM]:
        if target_result is None or target_result.status != TargetStatus.RESOLVED:
            actual_result = ResolutionResult(
                outcome=OutcomeType.NEEDS_CLARIFICATION,
                reason_code=(target_result.reason_code if target_result else "MISSING_TARGET")
            )
        elif op_type == OperationType.CHANGE_QUANTITY and quantity is None:
            actual_result = ResolutionResult(
                outcome=OutcomeType.NEEDS_CLARIFICATION,
                reason_code="MISSING_QUANTITY"
            )
        elif op_type == OperationType.REPLACE_ITEM and not product_id:
            actual_result = ResolutionResult(
                outcome=OutcomeType.NEEDS_CLARIFICATION,
                reason_code="AMBIGUOUS_PRODUCT"
            )
        else:
            operation = {
                "type": op_type.value,
                "product_id": product_id,
                "product_term": product_term,
                "target_item_id": target_selected_id,
                "quantity_value": quantity,
                "quantity_unit": unit,
                "replacement_product_id": product_id if op_type == OperationType.REPLACE_ITEM else None,
            }
            actual_result = ResolutionResult(
                outcome=OutcomeType.OPERATION,
                operation=operation,
                evidence=["interpretation"]
            )
    elif op_type == OperationType.ADD_ITEM:
        if not product_id:
            actual_result = ResolutionResult(
                outcome=OutcomeType.NEEDS_CLARIFICATION,
                reason_code="AMBIGUOUS_PRODUCT"
            )
        else:
            operation = {
                "type": op_type.value,
                "product_id": product_id,
                "product_term": product_term,
                "target_item_id": None,
                "quantity_value": quantity,
                "quantity_unit": unit,
                "replacement_product_id": None,
            }
            actual_result = ResolutionResult(
                outcome=OutcomeType.OPERATION,
                operation=operation,
                evidence=["interpretation"]
            )
    elif op_type in [OperationType.CONFIRM_ORDER, OperationType.CANCEL_ORDER]:
        operation = {
            "type": op_type.value,
            "product_id": None,
            "product_term": None,
            "target_item_id": None,
            "quantity_value": None,
            "quantity_unit": None,
            "replacement_product_id": None,
        }
        actual_result = ResolutionResult(
            outcome=OutcomeType.OPERATION,
            operation=operation,
            evidence=["interpretation"]
        )
    else:
        actual_result = ResolutionResult(
            outcome=OutcomeType.NEEDS_CLARIFICATION,
            reason_code="INTENT_NOT_RECOGNIZED"
        )

    # 6. Avaliação canônica
    comparison = evaluate_resolution(expected, actual_result)

    # 7. Monta o trace
    trace = {
        "case_id": case["id"],
        "message": message,
        "state_before": state_before.to_dict(),
        "expected": expected,
        "intent_signal": intent,
        "entity_signals": {
            "product_term": product_term,
            "brand": brand,
            "presentation": presentation,
            "quantity": quantity,
            "unit": unit,
        },
        "reference_signal": {
            "type": ref_signal.type.value if ref_signal else "UNKNOWN",
            "product_term": ref_signal.product_term if ref_signal else None,
        },
        "catalog_candidates": catalog_candidates,
        "product_resolution_status": product_resolution_status,
        "target_candidates": [item.id for item in state_before.items],
        "target_selected": target_selected_id,
        "target_evidence": target_evidence,
        "target_source": target_source,
        "actual_result": {
            "outcome": actual_result.outcome.value,
            "operation": actual_result.operation,
            "reason_code": actual_result.reason_code
        },
        "comparison": comparison,
        "exact_match": comparison["exact_match"],
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

    output_path = Path("reports/dev_diagnostic.json")
    with open(output_path, "w") as f:
        json.dump(traces, f, indent=2, ensure_ascii=False, default=str)
    print(f"Relatório salvo em {output_path}")

    total = len(traces)
    exact_matches = sum(1 for t in traces if t["exact_match"])
    print(f"\nTotal: {total}")
    print(f"Exact Matches: {exact_matches} ({exact_matches/total*100:.1f}%)")

    print("\nTarget Source Distribution:")
    target_sources = defaultdict(int)
    for t in traces:
        target_sources[t["target_source"]] += 1
    for source, count in sorted(target_sources.items()):
        print(f"  {source}: {count}")

    clarification_cases = [t for t in traces if t["expected"]["outcome"] == "NEEDS_CLARIFICATION"]
    if clarification_cases:
        print(f"\nNEEDS_CLARIFICATION cases ({len(clarification_cases)}):")
        for t in clarification_cases:
            actual_outcome = t["actual_result"]["outcome"]
            match = t["exact_match"]
            reason_exp = t["expected"].get("reason_code", "-")
            reason_act = t["actual_result"].get("reason_code", "-")
            print(f"  {t['case_id']}: expected {reason_exp}, got {reason_act} {'✅' if match else '❌'}")

if __name__ == "__main__":
    main()