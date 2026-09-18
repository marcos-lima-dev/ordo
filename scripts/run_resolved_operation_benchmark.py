import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from typing import Dict, List, Any
from collections import defaultdict

from order.state import OrderState, OrderItem
from order.resolution_result import ResolutionResult, OutcomeType
from order.resolution_evaluator import evaluate_resolution
from order.pending import PendingResolution
from pipeline.resolution_pipeline import resolve_operation


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
            needs_clarification=item_data.get("needs_clarification", False),
        )
        state.add_item(item)
    state.status = state_data.get("status", "OPEN")
    pending_data = state_data.get("pending_resolution")
    if pending_data:
        state.pending_resolution = PendingResolution(
            product_term=pending_data.get("product_term"),
            quantity=pending_data.get("quantity"),
            unit=pending_data.get("unit"),
            brand=pending_data.get("brand"),
            presentation=pending_data.get("presentation"),
            missing_fields=pending_data.get("missing_fields", []),
            reason=pending_data.get("reason", "AMBIGUOUS"),
        )
    return state


def compute_metrics(results):
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
        "by_type": {k: {"total": v["total"], "correct": v["correct"], "accuracy": v["correct"]/v["total"] if v["total"] > 0 else 0} for k, v in by_type.items()},
        "by_outcome": {k: {"total": v["total"], "correct": v["correct"], "accuracy": v["correct"]/v["total"] if v["total"] > 0 else 0} for k, v in by_outcome.items()},
    }


def main():
    dev_cases = load_benchmark("datasets/resolved_operation_dev_v2.jsonl")
    holdout_cases = load_benchmark("datasets/resolved_operation_holdout1_v2.jsonl")
    print(f"DEV (V2): {len(dev_cases)} casos")
    print(f"HOLDOUT-1 (V2): {len(holdout_cases)} casos")

    dev_results = []
    for case in dev_cases:
        state = build_state(case["state_before"])
        actual = resolve_operation(case["message"], state)
        comparison = evaluate_resolution(case["expected"], actual)
        dev_results.append({
            "id": case["id"],
            "match": comparison["exact_match"],
            "details": comparison["details"],
            "expected": case["expected"],
            "actual": {"outcome": actual.outcome.value, "operation": actual.operation, "reason_code": actual.reason_code},
        })

    holdout_results = []
    for case in holdout_cases:
        state = build_state(case["state_before"])
        actual = resolve_operation(case["message"], state)
        comparison = evaluate_resolution(case["expected"], actual)
        holdout_results.append({
            "id": case["id"],
            "match": comparison["exact_match"],
            "details": comparison["details"],
            "expected": case["expected"],
            "actual": {"outcome": actual.outcome.value, "operation": actual.operation, "reason_code": actual.reason_code},
        })

    dev_metrics = compute_metrics(dev_results)
    holdout_metrics = compute_metrics(holdout_results)

    print("\n" + "=" * 60)
    print("RESOLVED OPERATION BENCHMARK — V2")
    print("=" * 60)
    print("\n--- DEV V2 ---")
    print(f"Total: {dev_metrics['total']}")
    print(f"Exact Matches: {dev_metrics['exact_matches']}/{dev_metrics['total']} ({dev_metrics['accuracy']*100:.1f}%)")
    for op_type, data in dev_metrics["by_type"].items():
        print(f"  {op_type}: {data['correct']}/{data['total']} ({data['accuracy']*100:.1f}%)")
    print("\n--- HOLDOUT-1 V2 ---")
    print(f"Total: {holdout_metrics['total']}")
    print(f"Exact Matches: {holdout_metrics['exact_matches']}/{holdout_metrics['total']} ({holdout_metrics['accuracy']*100:.1f}%)")
    for op_type, data in holdout_metrics["by_type"].items():
        print(f"  {op_type}: {data['correct']}/{data['total']} ({data['accuracy']*100:.1f}%)")

    output_path = Path("reports/resolved_operation_benchmark_v2.json")
    with open(output_path, "w") as f:
        json.dump({"dev": {"results": dev_results, "metrics": dev_metrics}, "holdout": {"results": holdout_results, "metrics": holdout_metrics}}, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nResultados salvos em {output_path}")


if __name__ == "__main__":
    main()