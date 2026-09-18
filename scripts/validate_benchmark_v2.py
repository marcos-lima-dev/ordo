import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json

VALID_OPERATION_TYPES = {
    "ADD_ITEM", "REMOVE_ITEM", "CHANGE_QUANTITY", "REPLACE_ITEM",
    "CONFIRM_ORDER", "CANCEL_ORDER"
}
VALID_REASON_CODES = {
    "MISSING_TARGET", "AMBIGUOUS_TARGET", "MISSING_PRODUCT",
    "AMBIGUOUS_PRODUCT", "MISSING_QUANTITY", "PENDING_RESOLUTION",
    "AMBIGUOUS_OPERATION"
}
VALID_OUTCOMES = {"OPERATION", "NEEDS_CLARIFICATION", "BLOCKED", "NO_OP"}

def load_catalog_ids():
    with open("data/catalog.json") as f:
        return {p["product_id"] for p in json.load(f)}

def validate(path, catalog_ids):
    errors = []
    ids = set()
    with open(path) as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                case = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"{path}:{n} JSON inválido: {e}")
                continue

            cid = case.get("id")
            if cid in ids:
                errors.append(f"{path}:{n} ID duplicado: {cid}")
            ids.add(cid)

            exp = case.get("expected", {})
            outcome = exp.get("outcome")
            if outcome not in VALID_OUTCOMES:
                errors.append(f"{cid}: outcome inválido: {outcome}")

            if outcome == "OPERATION":
                op = exp.get("operation") or {}
                op_type = op.get("type")
                if op_type not in VALID_OPERATION_TYPES:
                    errors.append(f"{cid}: operation type inválido: {op_type}")
                for field in ["product_id", "replacement_product_id"]:
                    pid = op.get(field)
                    if pid and pid not in catalog_ids:
                        errors.append(f"{cid}: {field} inválido: {pid}")

            if outcome == "NEEDS_CLARIFICATION":
                reason = exp.get("reason_code")
                if reason not in VALID_REASON_CODES:
                    errors.append(f"{cid}: reason_code inválido: {reason}")

    return ids, errors

def main():
    catalog_ids = load_catalog_ids()
    all_errors = []

    for path in [
        "datasets/resolved_operation_dev_v2.jsonl",
        "datasets/resolved_operation_holdout1_v2.jsonl",
    ]:
        ids, errors = validate(path, catalog_ids)
        print(f"{path}: {len(ids)} casos, {len(errors)} erros")
        all_errors.extend(errors)

    if all_errors:
        print("\n=== ERROS ===")
        for e in all_errors:
            print(f"  {e}")
        sys.exit(1)
    else:
        print("\nRESULT: PASS")

if __name__ == "__main__":
    main()