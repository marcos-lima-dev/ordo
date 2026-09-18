import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from typing import Dict, List, Any
from collections import defaultdict

from order.state import OrderState, OrderItem
from order.pending import PendingResolution
from order.resolution_evaluator import evaluate_resolution
from pipeline.resolution_pipeline import resolve_operation


def load_holdout2():
    path = Path("datasets/resolved_operation_holdout2.jsonl")
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def build_state(state_data):
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


def main():
    cases = load_holdout2()
    print(f"HOLDOUT-2 BLIND GATE — {len(cases)} casos\n")

    results = []
    for case in cases:
        state = build_state(case["state_before"])
        actual = resolve_operation(case["message"], state)
        comparison = evaluate_resolution(case["expected"], actual)
        results.append({
            "id": case["id"],
            "message": case["message"],
            "expected": case["expected"],
            "actual": {
                "outcome": actual.outcome.value,
                "operation": actual.operation,
                "reason_code": actual.reason_code,
            },
            "exact_match": comparison["exact_match"],
            "details": comparison["details"],
        })

    total = len(results)
    exact = sum(1 for r in results if r["exact_match"])

    by_type = defaultdict(lambda: {"total": 0, "correct": 0})
    wrong_executable = 0
    unnecessary_clarification = 0

    for r in results:
        exp = r["expected"]
        act = r["actual"]
        exp_op = exp.get("operation")
        exp_type = exp_op.get("type") if exp_op else "NEEDS_CLARIFICATION"
        by_type[exp_type]["total"] += 1
        if r["exact_match"]:
            by_type[exp_type]["correct"] += 1

        if exp.get("outcome") == "NEEDS_CLARIFICATION" and act["outcome"] == "OPERATION":
            wrong_executable += 1
        if exp.get("outcome") == "OPERATION" and act["outcome"] == "NEEDS_CLARIFICATION":
            unnecessary_clarification += 1

    print(f"Raw Blind Exact Match: {exact}/{total} ({exact/total*100:.1f}%)\n")

    print("Por OperationType (expected):")
    for k in ["ADD_ITEM", "REMOVE_ITEM", "CHANGE_QUANTITY", "REPLACE_ITEM",
              "CONFIRM_ORDER", "CANCEL_ORDER", "NEEDS_CLARIFICATION"]:
        if k in by_type:
            d = by_type[k]
            print(f"  {k}: {d['correct']}/{d['total']} ({d['correct']/d['total']*100:.1f}%)")

    print(f"\nWrong Executable Operation: {wrong_executable}")
    print(f"Unnecessary Clarification: {unnecessary_clarification}")

    print("\n=== MATRIZ COMPLETA ===")
    for r in results:
        status = "PASS" if r["exact_match"] else "FAIL"
        print(f"\n{r['id']} [{status}]: {r['message']}")
        print(f"  expected: {r['expected']}")
        print(f"  actual:   {r['actual']}")
        if not r["exact_match"]:
            print(f"  details:  {r['details']}")

    output_path = Path("reports/holdout2_blind_gate.json")
    with open(output_path, "w") as f:
        json.dump({
            "total": total,
            "exact_match": exact,
            "accuracy": exact/total,
            "wrong_executable_operation": wrong_executable,
            "unnecessary_clarification": unnecessary_clarification,
            "by_type": dict(by_type),
            "results": results,
        }, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n\nRelatório salvo em {output_path}")


if __name__ == "__main__":
    main()