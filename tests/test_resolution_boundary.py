import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from order.resolution_result import ResolutionResult, OutcomeType
from order.resolved_operation import ResolvedOperation, OperationType
from order.resolution_boundary import to_resolved_operation


# =============================================
# Helpers
# =============================================

def op_result(op_dict, reason_code=None, evidence=None):
    return ResolutionResult(
        outcome=OutcomeType.OPERATION,
        operation=op_dict,
        reason_code=reason_code,
        evidence=evidence or [],
    )


def clarify_result(reason_code="AMBIGUOUS_PRODUCT"):
    return ResolutionResult(
        outcome=OutcomeType.NEEDS_CLARIFICATION,
        operation=None,
        reason_code=reason_code,
    )


# =============================================
# Happy paths
# =============================================

def test_valid_add_item_maps_to_resolved_operation():
    result = op_result({
        "type": "ADD_ITEM",
        "product_id": "CQ-29",
        "product_term": "Manteiga s/sal",
        "quantity_value": 10.0,
        "quantity_unit": "KG",
    })
    op = to_resolved_operation(result)
    assert op is not None
    assert isinstance(op, ResolvedOperation)
    assert op.type == OperationType.ADD_ITEM
    assert op.product_id == "CQ-29"
    assert op.product_term == "Manteiga s/sal"
    assert op.quantity_value == 10.0
    assert op.quantity_unit == "KG"
    assert op.is_valid() is True


def test_valid_remove_item_maps_to_resolved_operation():
    result = op_result({
        "type": "REMOVE_ITEM",
        "target_item_id": "item_1",
    })
    op = to_resolved_operation(result)
    assert op is not None
    assert op.type == OperationType.REMOVE_ITEM
    assert op.target_item_id == "item_1"
    assert op.is_valid() is True


def test_valid_change_quantity_with_explicit_unit_maps():
    result = op_result({
        "type": "CHANGE_QUANTITY",
        "target_item_id": "item_1",
        "quantity_value": 3.0,
        "quantity_unit": "KG",
    })
    op = to_resolved_operation(result)
    assert op is not None
    assert op.type == OperationType.CHANGE_QUANTITY
    assert op.quantity_value == 3.0
    assert op.quantity_unit == "KG"
    assert op.is_valid() is True


def test_valid_change_quantity_with_unit_none_maps_keep_existing_unit():
    """quantity_unit=None → KEEP_EXISTING_UNIT (P2)."""
    result = op_result({
        "type": "CHANGE_QUANTITY",
        "target_item_id": "item_1",
        "quantity_value": 5.0,
        "quantity_unit": None,
    })
    op = to_resolved_operation(result)
    assert op is not None
    assert op.quantity_value == 5.0
    assert op.quantity_unit is None
    assert op.is_valid() is True


def test_valid_replace_item_maps():
    result = op_result({
        "type": "REPLACE_ITEM",
        "target_item_id": "item_1",
        "replacement_product_id": "CQ-46",
        "product_term": "Provolone Riqueza de Minas",
    })
    op = to_resolved_operation(result)
    assert op is not None
    assert op.type == OperationType.REPLACE_ITEM
    assert op.target_item_id == "item_1"
    assert op.replacement_product_id == "CQ-46"
    assert op.is_valid() is True


def test_confirm_order_maps():
    result = op_result({"type": "CONFIRM_ORDER"})
    op = to_resolved_operation(result)
    assert op is not None
    assert op.type == OperationType.CONFIRM_ORDER
    assert op.is_valid() is True


def test_cancel_order_maps():
    result = op_result({"type": "CANCEL_ORDER"})
    op = to_resolved_operation(result)
    assert op is not None
    assert op.type == OperationType.CANCEL_ORDER
    assert op.is_valid() is True


# =============================================
# Rejeições
# =============================================

def test_partial_add_item_does_not_cross_boundary():
    """ADD_ITEM com product_id=None não é executável (Stage 1A)."""
    result = op_result({
        "type": "ADD_ITEM",
        "product_id": None,
        "product_term": "provolone",
        "quantity_value": 5.0,
        "quantity_unit": "KG",
    })
    op = to_resolved_operation(result)
    assert op is None


def test_unknown_does_not_cross_boundary():
    result = op_result({"type": "UNKNOWN"})
    op = to_resolved_operation(result)
    assert op is None


def test_needs_clarification_does_not_cross_boundary():
    result = clarify_result("AMBIGUOUS_PRODUCT")
    op = to_resolved_operation(result)
    assert op is None


def test_operation_none_does_not_cross_boundary():
    """OPERATION com operation=None — defensivo."""
    result = ResolutionResult(
        outcome=OutcomeType.OPERATION,
        operation=None,
    )
    op = to_resolved_operation(result)
    assert op is None


def test_non_dict_operation_does_not_cross_boundary():
    result = ResolutionResult(
        outcome=OutcomeType.OPERATION,
        operation="not a dict",
    )
    op = to_resolved_operation(result)
    assert op is None


def test_missing_type_does_not_cross_boundary():
    result = op_result({"product_id": "CQ-29"})
    op = to_resolved_operation(result)
    assert op is None


def test_non_string_type_does_not_cross_boundary():
    result = op_result({"type": 42, "product_id": "CQ-29"})
    op = to_resolved_operation(result)
    assert op is None


def test_unknown_type_string_does_not_cross_boundary():
    result = op_result({"type": "NOT_A_REAL_TYPE"})
    op = to_resolved_operation(result)
    assert op is None


def test_incomplete_change_quantity_does_not_cross_boundary():
    """CHANGE_QUANTITY sem quantity_value — inválida."""
    result = op_result({
        "type": "CHANGE_QUANTITY",
        "target_item_id": "item_1",
    })
    op = to_resolved_operation(result)
    assert op is None


def test_incomplete_remove_item_does_not_cross_boundary():
    """REMOVE_ITEM sem target_item_id — inválida."""
    result = op_result({"type": "REMOVE_ITEM"})
    op = to_resolved_operation(result)
    assert op is None


# =============================================
# Pós-condição global
# =============================================

def test_every_returned_operation_is_valid():
    cases = [
        op_result({"type": "ADD_ITEM", "product_id": "CQ-29"}),
        op_result({"type": "REMOVE_ITEM", "target_item_id": "item_1"}),
        op_result({"type": "CHANGE_QUANTITY", "target_item_id": "item_1", "quantity_value": 3.0}),
        op_result({"type": "CHANGE_QUANTITY", "target_item_id": "item_1", "quantity_value": 5.0, "quantity_unit": "KG"}),
        op_result({"type": "REPLACE_ITEM", "target_item_id": "item_1", "replacement_product_id": "CQ-46"}),
        op_result({"type": "CONFIRM_ORDER"}),
        op_result({"type": "CANCEL_ORDER"}),
    ]
    for r in cases:
        op = to_resolved_operation(r)
        assert op is not None
        assert op.is_valid() is True


# =============================================
# Determinismo
# =============================================

def test_determinism_same_input_semantically_equal_output():
    result = op_result({
        "type": "ADD_ITEM",
        "product_id": "CQ-29",
        "product_term": "Manteiga s/sal",
        "quantity_value": 10.0,
        "quantity_unit": "KG",
    })
    op1 = to_resolved_operation(result)
    op2 = to_resolved_operation(result)
    assert op1 is not None and op2 is not None
    assert op1.type == op2.type
    assert op1.product_id == op2.product_id
    assert op1.product_term == op2.product_term
    assert op1.target_item_id == op2.target_item_id
    assert op1.quantity_value == op2.quantity_value
    assert op1.quantity_unit == op2.quantity_unit
    assert op1.replacement_product_id == op2.replacement_product_id
    assert op1.source_message_id == op2.source_message_id


# =============================================
# Não-mutação e source_message_id
# =============================================

def test_boundary_does_not_mutate_result_operation():
    op_dict = {
        "type": "ADD_ITEM",
        "product_id": "CQ-29",
        "product_term": "Manteiga s/sal",
    }
    snapshot = dict(op_dict)
    result = ResolutionResult(outcome=OutcomeType.OPERATION, operation=op_dict)
    _ = to_resolved_operation(result)
    assert op_dict == snapshot


def test_source_message_id_is_none_reserved_non_operational():
    """P6: RESERVED / NON-OPERATIONAL. Não inventar valor."""
    result = op_result({"type": "ADD_ITEM", "product_id": "CQ-29"})
    op = to_resolved_operation(result)
    assert op is not None
    assert op.source_message_id is None