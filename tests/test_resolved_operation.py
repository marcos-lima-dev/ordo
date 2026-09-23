import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from order.resolved_operation import ResolvedOperation, OperationType
from order.operation_fields import (
    EXECUTION_REQUIREMENTS,
    NON_EXECUTABLE_OPERATION_TYPES,
)


# =============================================
# UNKNOWN — nunca executável
# =============================================

def test_unknown_is_never_valid():
    op = ResolvedOperation(type=OperationType.UNKNOWN)
    assert op.is_valid() is False


def test_unknown_is_declared_non_executable():
    assert OperationType.UNKNOWN in NON_EXECUTABLE_OPERATION_TYPES


def test_unknown_is_not_in_execution_requirements():
    assert OperationType.UNKNOWN not in EXECUTION_REQUIREMENTS


# =============================================
# ADD_ITEM
# =============================================

def test_add_item_with_product_id_is_valid():
    op = ResolvedOperation(type=OperationType.ADD_ITEM, product_id="CQ-29")
    assert op.is_valid() is True


def test_add_item_without_product_id_is_invalid():
    op = ResolvedOperation(
        type=OperationType.ADD_ITEM,
        product_term="provolone",
        quantity_value=5.0,
        quantity_unit="KG",
    )
    assert op.is_valid() is False


# =============================================
# REMOVE_ITEM
# =============================================

def test_remove_item_with_target_is_valid():
    op = ResolvedOperation(type=OperationType.REMOVE_ITEM, target_item_id="item_1")
    assert op.is_valid() is True


def test_remove_item_without_target_is_invalid():
    op = ResolvedOperation(type=OperationType.REMOVE_ITEM)
    assert op.is_valid() is False


# =============================================
# CHANGE_QUANTITY
# =============================================

def test_change_quantity_with_unit_is_valid():
    op = ResolvedOperation(
        type=OperationType.CHANGE_QUANTITY,
        target_item_id="item_1",
        quantity_value=3.0,
        quantity_unit="KG",
    )
    assert op.is_valid() is True


def test_change_quantity_without_unit_is_valid_keep_existing_unit():
    op = ResolvedOperation(
        type=OperationType.CHANGE_QUANTITY,
        target_item_id="item_1",
        quantity_value=3.0,
        quantity_unit=None,
    )
    assert op.is_valid() is True


def test_change_quantity_without_value_is_invalid():
    op = ResolvedOperation(
        type=OperationType.CHANGE_QUANTITY,
        target_item_id="item_1",
    )
    assert op.is_valid() is False


def test_change_quantity_without_target_is_invalid():
    op = ResolvedOperation(
        type=OperationType.CHANGE_QUANTITY,
        quantity_value=3.0,
    )
    assert op.is_valid() is False


# =============================================
# REPLACE_ITEM
# =============================================

def test_replace_item_with_target_and_replacement_is_valid():
    op = ResolvedOperation(
        type=OperationType.REPLACE_ITEM,
        target_item_id="item_1",
        replacement_product_id="CQ-46",
    )
    assert op.is_valid() is True


def test_replace_item_without_replacement_is_invalid():
    op = ResolvedOperation(
        type=OperationType.REPLACE_ITEM,
        target_item_id="item_1",
    )
    assert op.is_valid() is False


def test_replace_item_without_target_is_invalid():
    op = ResolvedOperation(
        type=OperationType.REPLACE_ITEM,
        replacement_product_id="CQ-46",
    )
    assert op.is_valid() is False


# =============================================
# CONFIRM_ORDER / CANCEL_ORDER
# =============================================

def test_confirm_order_is_valid():
    op = ResolvedOperation(type=OperationType.CONFIRM_ORDER)
    assert op.is_valid() is True


def test_cancel_order_is_valid():
    op = ResolvedOperation(type=OperationType.CANCEL_ORDER)
    assert op.is_valid() is True


# =============================================
# SINGLE SOURCE OF TRUTH
# =============================================

def test_execution_requirements_declares_expected_values():
    """A declaração deve refletir o contrato normativo do Stage 1A."""
    assert EXECUTION_REQUIREMENTS[OperationType.ADD_ITEM] == ["product_id"]
    assert EXECUTION_REQUIREMENTS[OperationType.REMOVE_ITEM] == ["target_item_id"]
    assert EXECUTION_REQUIREMENTS[OperationType.CHANGE_QUANTITY] == [
        "target_item_id",
        "quantity_value",
    ]
    assert EXECUTION_REQUIREMENTS[OperationType.REPLACE_ITEM] == [
        "target_item_id",
        "replacement_product_id",
    ]
    assert EXECUTION_REQUIREMENTS[OperationType.CONFIRM_ORDER] == []
    assert EXECUTION_REQUIREMENTS[OperationType.CANCEL_ORDER] == []


def test_change_quantity_unit_is_not_declared_as_required():
    """quantity_unit=None → KEEP_EXISTING_UNIT; não pode estar em required."""
    assert "quantity_unit" not in EXECUTION_REQUIREMENTS[OperationType.CHANGE_QUANTITY]