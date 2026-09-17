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

# =============================================
# Carregamento dos datasets
# =============================================

def load_benchmark(path: str) -> List[Dict[str, Any]]:
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
# Pipeline upstream (gera ResolutionResult)
# =============================================

_adapter = None
_resolver = None
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

def get_target_resolver():
    global _target_resolver
    if _target_resolver is None:
        _target_resolver = TargetResolver()
    return _target_resolver

def resolve_operation(message: str, state: OrderState) -> ResolutionResult:
    adapter = get_adapter()
    resolver = get_resolver()
    target_resolver = get_target_resolver()

    ref_signal = resolver.resolve(message, state)
    interpretation = adapter.predict(message)
    intent = interpretation.get("intent")

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
        return ResolutionResult(
            outcome=OutcomeType.NEEDS_CLARIFICATION,
            reason_code="INTENT_NOT_RECOGNIZED"
        )

    product_term = interpretation.get("product_term")
    quantity = interpretation.get("quantity", {}).get("value")
    unit = interpretation.get("quantity", {}).get("unit")
    candidates = interpretation.get("catalog_candidates", [])

    # ---------------------------------------------------------------
    # Target Resolution para operações que atuam sobre item existente
    # ---------------------------------------------------------------
    target_id = None
    if op_type in [OperationType.REMOVE_ITEM, OperationType.CHANGE_QUANTITY, OperationType.REPLACE_ITEM]:
        target_result = target_resolver.resolve(
            message=message,
            state=state,
            reference_product_term=product_term,
            ref_signal=ref_signal,
        )
        if target_result.status != TargetStatus.RESOLVED:
            return ResolutionResult(
                outcome=OutcomeType.NEEDS_CLARIFICATION,
                reason_code=target_result.reason_code or "MISSING_TARGET"
            )
        target_id = target_result.target_item_id

    # ---------------------------------------------------------------
    # Product Resolution (para ADD_ITEM e REPLACE_ITEM destination)
    # ---------------------------------------------------------------
    product_id = None
    if candidates and len(candidates) == 1:
        product_id = candidates[0]

    # Validação por tipo de operação
    if op_type == OperationType.ADD_ITEM and not product_id:
        return ResolutionResult(
            outcome=OutcomeType.NEEDS_CLARIFICATION,
            reason_code="AMBIGUOUS_PRODUCT"
        )

    if op_type == OperationType.CHANGE_QUANTITY and quantity is None:
        return ResolutionResult(
            outcome=OutcomeType.NEEDS_CLARIFICATION,
            reason_code="MISSING_QUANTITY"
        )

    if op_type == OperationType.REPLACE_ITEM and not product_id:
        return ResolutionResult(
            outcome=OutcomeType.NEEDS_CLARIFICATION,
            reason_code="AMBIGUOUS_PRODUCT"
        )

    operation = {
        "type": op_type.value,
        "product_id": product_id,
        "product_term": product_term,
        "target_item_id": target_id,
        "quantity_value": quantity,
        "quantity_unit": unit,
        "replacement_product_id": product_id if op_type == OperationType.REPLACE_ITEM else None,
    }

    return ResolutionResult(
        outcome=OutcomeType.OPERATION,
        operation=operation,
        evidence=["interpretation"]
    )

# =============================================
# Métricas
# =============================================

def compute_metrics(results: List[Dict]) -> Dict[str, Any]:
    total = len(results)
    exact_matches = sum(1 for r in results if r["match"])
    by_type = defaultdict(lambda: {"total": 0, "correct": 0})
    by_outcome = defaultdict(lambda: {"total": 0, "correct": 0})

    for r in results:
        exp = r["expected"]
        exp_op = exp.get("operation")
        op_type = exp_op.get("type") if exp_op else "NEEDS_CLARIFICATION"
        by_type[op_type]["total"] += 1
        if r["match"]:
            by_type[op_type]["correct"] += 1

        outcome = exp.get("outcome", "UNKNOWN")
        by_outcome[outcome]["total"] += 1
        if r["match"]:
            by_outcome[outcome]["correct"] += 1

    return {
        "total": total,
        "exact_matches": exact_matches,
        "accuracy": exact_matches / total if total > 0 else 0,
        "by_type": {k: {"total": v["total"], "correct": v["correct"], "accuracy": v["correct"]/v["total"] if v["total"]>0 else 0} for k, v in by_type.items()},
        "by_outcome": {k: {"total": v["total"], "correct": v["correct"], "accuracy": v["correct"]/v["total"] if v["total"]>0 else 0} for k, v in by_outcome.items()}
    }

# =============================================
# Main
# =============================================

def main():
    dev_path = Path("datasets/resolved_operation_dev.jsonl")
    holdout_path = Path("datasets/resolved_operation_holdout.jsonl")

    dev_cases = load_benchmark(dev_path)
    holdout_cases = load_benchmark(holdout_path)

    print(f"DEV: {len(dev_cases)} casos")
    print(f"HOLDOUT: {len(holdout_cases)} casos")

    dev_results = []
    for case in dev_cases:
        state = build_state(case["state_before"])
        message = case["message"]
        expected = case["expected"]
        actual = resolve_operation(message, state)
        comparison = evaluate_resolution(expected, actual)
        dev_results.append({
            "id": case["id"],
            "match": comparison["exact_match"],
            "details": comparison["details"],
            "expected": expected,
            "actual": {
                "outcome": actual.outcome.value,
                "operation": actual.operation,
                "reason_code": actual.reason_code
            }
        })

    dev_metrics = compute_metrics(dev_results)

    holdout_results = []
    for case in holdout_cases:
        state = build_state(case["state_before"])
        message = case["message"]
        expected = case["expected"]
        actual = resolve_operation(message, state)
        comparison = evaluate_resolution(expected, actual)
        holdout_results.append({
            "id": case["id"],
            "match": comparison["exact_match"],
            "details": comparison["details"],
            "expected": expected,
            "actual": {
                "outcome": actual.outcome.value,
                "operation": actual.operation,
                "reason_code": actual.reason_code
            }
        })

    holdout_metrics = compute_metrics(holdout_results)

    print("\n" + "="*60)
    print("RESOLVED OPERATION BENCHMARK - BASELINE CANÔNICA")
    print("="*60)

    print("\n--- DEV ---")
    print(f"Total: {dev_metrics['total']}")
    print(f"Exact Matches: {dev_metrics['exact_matches']}/{dev_metrics['total']} ({dev_metrics['accuracy']*100:.1f}%)")
    print("\nPor tipo de operação:")
    for op_type, data in dev_metrics["by_type"].items():
        print(f"  {op_type}: {data['correct']}/{data['total']} ({data['accuracy']*100:.1f}%)")

    print("\n--- HOLDOUT ---")
    print(f"Total: {holdout_metrics['total']}")
    print(f"Exact Matches: {holdout_metrics['exact_matches']}/{holdout_metrics['total']} ({holdout_metrics['accuracy']*100:.1f}%)")
    print("\nPor tipo de operação:")
    for op_type, data in holdout_metrics["by_type"].items():
        print(f"  {op_type}: {data['correct']}/{data['total']} ({data['accuracy']*100:.1f}%)")

    output_path = Path("reports/resolved_operation_benchmark.json")
    with open(output_path, "w") as f:
        json.dump({
            "dev": {"results": dev_results, "metrics": dev_metrics},
            "holdout": {"results": holdout_results, "metrics": holdout_metrics}
        }, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nResultados salvos em {output_path}")

if __name__ == "__main__":
    main()