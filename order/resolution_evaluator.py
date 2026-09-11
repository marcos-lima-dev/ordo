from typing import Dict, Any, Optional
from order.resolution_result import ResolutionResult, OutcomeType
from order.operation_fields import REQUIRED_FIELDS_BY_TYPE

def evaluate_resolution(expected: Dict[str, Any], actual: ResolutionResult) -> Dict[str, Any]:
    result = {
        "outcome_match": False,
        "operation_type_match": False,
        "target_match": False,
        "product_match": False,
        "quantity_match": False,
        "unit_match": False,
        "reason_code_match": False,
        "exact_match": False,
        "details": []
    }

    expected_outcome = expected.get("outcome", "UNKNOWN")
    actual_outcome = actual.outcome.value
    result["outcome_match"] = (expected_outcome == actual_outcome)
    if not result["outcome_match"]:
        result["details"].append(f"outcome mismatch: expected {expected_outcome}, got {actual_outcome}")
        return result

    if expected_outcome == "NEEDS_CLARIFICATION":
        expected_reason = expected.get("reason_code")
        actual_reason = actual.reason_code
        result["reason_code_match"] = (expected_reason == actual_reason)
        if not result["reason_code_match"]:
            result["details"].append(f"reason_code mismatch: expected {expected_reason}, got {actual_reason}")
        else:
            result["exact_match"] = True
        return result

    expected_op = expected.get("operation")
    if expected_op is None:
        result["details"].append("expected operation not found")
        return result

    actual_op = actual.operation
    if actual_op is None:
        result["details"].append("actual operation is None")
        return result

    exp_type = expected_op.get("type")
    act_type = actual_op.get("type")
    result["operation_type_match"] = (exp_type == act_type)
    if not result["operation_type_match"]:
        result["details"].append(f"type mismatch: expected {exp_type}, got {act_type}")
        return result

    required_fields = REQUIRED_FIELDS_BY_TYPE.get(exp_type, [])
    for field in required_fields:
        exp_val = expected_op.get(field)
        act_val = actual_op.get(field)
        if exp_val != act_val:
            result["details"].append(f"{field} mismatch: expected {exp_val}, got {act_val}")
            return result

    result["target_match"] = (expected_op.get("target_item_id") == actual_op.get("target_item_id"))

    if exp_type in ["CHANGE_QUANTITY", "ADD_ITEM"]:
        exp_qty = expected_op.get("quantity_value")
        act_qty = actual_op.get("quantity_value")
        result["quantity_match"] = (exp_qty == act_qty)
        if not result["quantity_match"]:
            result["details"].append(f"quantity mismatch: expected {exp_qty}, got {act_qty}")
            return result

        exp_unit = expected_op.get("quantity_unit")
        act_unit = actual_op.get("quantity_unit")
        result["unit_match"] = (exp_unit == act_unit)
        if not result["unit_match"]:
            result["details"].append(f"unit mismatch: expected {exp_unit}, got {act_unit}")
            return result

    if exp_type in ["ADD_ITEM", "REPLACE_ITEM"]:
        exp_product = expected_op.get("product_id")
        act_product = actual_op.get("product_id")
        result["product_match"] = (exp_product == act_product)
        if not result["product_match"]:
            result["details"].append(f"product mismatch: expected {exp_product}, got {act_product}")
            return result

    result["exact_match"] = True
    return result