import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from typing import Dict, List, Any
from collections import defaultdict

from order.state import OrderState, OrderItem
from order.pending import PendingResolution
from pipeline.resolution_pipeline import resolve_operation


def load_dev_set():
    path = Path("datasets/resolved_operation_dev_v2.jsonl")
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


def main():
    dev_cases = load_dev_set()
    print(f"Diagnosticando {len(dev_cases)} casos do DEV (V2)...")

    traces = []
    for case in dev_cases:
        state = build_state(case["state_before"])
        actual = resolve_operation(case["message"], state)
        traces.append({
            "case_id": case["id"],
            "message": case["message"],
            "expected": case["expected"],
            "actual": {
                "outcome": actual.outcome.value,
                "operation": actual.operation,
                "reason_code": actual.reason_code,
            },
        })

    output_path = Path("reports/dev_diagnostic.json")
    with open(output_path, "w") as f:
        json.dump(traces, f, indent=2, ensure_ascii=False, default=str)
    print(f"Relatório salvo em {output_path}")

    total = len(traces)
    clarification_cases = [t for t in traces if t["expected"]["outcome"] == "NEEDS_CLARIFICATION"]
    print(f"\nTotal: {total}")
    print(f"\nNEEDS_CLARIFICATION cases ({len(clarification_cases)}):")
    for t in clarification_cases:
        reason_exp = t["expected"].get("reason_code", "-")
        reason_act = t["actual"].get("reason_code", "-")
        match = (reason_exp == reason_act)
        print(f"  {t['case_id']}: expected {reason_exp}, got {reason_act} {'✅' if match else '❌'}")


if __name__ == "__main__":
    main()