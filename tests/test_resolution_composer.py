import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from order.resolution_composer import ResolutionComposer
from order.resolved_operation import OperationType
from order.target_resolver import TargetStatus
from order.product_resolver import ResolutionStatus


@pytest.fixture
def composer():
    return ResolutionComposer()


# --- CHANGE_QUANTITY ---

def test_change_target_unknown(composer):
    r = composer.compose(
        OperationType.CHANGE_QUANTITY,
        target_status=TargetStatus.UNKNOWN,
    )
    assert r is not None
    assert r.reason_code == "MISSING_TARGET"


def test_change_target_ambiguous(composer):
    r = composer.compose(
        OperationType.CHANGE_QUANTITY,
        target_status=TargetStatus.AMBIGUOUS,
    )
    assert r is not None
    assert r.reason_code == "AMBIGUOUS_TARGET"


def test_change_ok(composer):
    r = composer.compose(
        OperationType.CHANGE_QUANTITY,
        target_status=TargetStatus.RESOLVED,
        quantity_value=4.0,
    )
    assert r is None


def test_change_missing_quantity(composer):
    r = composer.compose(
        OperationType.CHANGE_QUANTITY,
        target_status=TargetStatus.RESOLVED,
        quantity_value=None,
    )
    assert r is not None
    assert r.reason_code == "MISSING_QUANTITY"


# --- REMOVE_ITEM ---

def test_remove_target_unknown(composer):
    r = composer.compose(OperationType.REMOVE_ITEM, target_status=TargetStatus.UNKNOWN)
    assert r is not None
    assert r.reason_code == "MISSING_TARGET"


def test_remove_target_ambiguous(composer):
    r = composer.compose(OperationType.REMOVE_ITEM, target_status=TargetStatus.AMBIGUOUS)
    assert r is not None
    assert r.reason_code == "AMBIGUOUS_TARGET"


def test_remove_does_not_require_product(composer):
    """REMOVE_ITEM não exige produto novo: ausência de product não gera MISSING_PRODUCT."""
    r = composer.compose(
        OperationType.REMOVE_ITEM,
        target_status=TargetStatus.RESOLVED,
        product_status=None,
    )
    assert r is None


# --- ADD_ITEM ---

def test_add_product_not_found(composer):
    r = composer.compose(
        OperationType.ADD_ITEM,
        product_status=ResolutionStatus.NOT_FOUND,
    )
    assert r is not None
    assert r.reason_code == "MISSING_PRODUCT"


def test_add_product_ambiguous(composer):
    r = composer.compose(
        OperationType.ADD_ITEM,
        product_status=ResolutionStatus.AMBIGUOUS,
    )
    assert r is not None
    assert r.reason_code == "AMBIGUOUS_PRODUCT"


def test_add_ok(composer):
    r = composer.compose(
        OperationType.ADD_ITEM,
        product_status=ResolutionStatus.EXACT_MATCH,
    )
    assert r is None


# --- REPLACE_ITEM ---

def test_replace_source_unknown(composer):
    r = composer.compose(
        OperationType.REPLACE_ITEM,
        target_status=TargetStatus.UNKNOWN,
        product_status=ResolutionStatus.EXACT_MATCH,
    )
    assert r is not None
    assert r.reason_code == "MISSING_TARGET"


def test_replace_source_ambiguous(composer):
    r = composer.compose(
        OperationType.REPLACE_ITEM,
        target_status=TargetStatus.AMBIGUOUS,
        product_status=ResolutionStatus.EXACT_MATCH,
    )
    assert r is not None
    assert r.reason_code == "AMBIGUOUS_TARGET"


def test_replace_source_ok_destination_missing(composer):
    r = composer.compose(
        OperationType.REPLACE_ITEM,
        target_status=TargetStatus.RESOLVED,
        product_status=ResolutionStatus.NOT_FOUND,
    )
    assert r is not None
    assert r.reason_code == "MISSING_PRODUCT"


def test_replace_source_ok_destination_ambiguous(composer):
    r = composer.compose(
        OperationType.REPLACE_ITEM,
        target_status=TargetStatus.RESOLVED,
        product_status=ResolutionStatus.AMBIGUOUS,
    )
    assert r is not None
    assert r.reason_code == "AMBIGUOUS_PRODUCT"


def test_replace_ok(composer):
    r = composer.compose(
        OperationType.REPLACE_ITEM,
        target_status=TargetStatus.RESOLVED,
        product_status=ResolutionStatus.EXACT_MATCH,
    )
    assert r is None


# --- CONFIRM_ORDER / CANCEL_ORDER ---

def test_confirm_no_artificial_target(composer):
    r = composer.compose(OperationType.CONFIRM_ORDER)
    assert r is None


def test_cancel_no_artificial_target(composer):
    r = composer.compose(OperationType.CANCEL_ORDER)
    assert r is None


# --- Pending ---

def test_pending_blocking(composer):
    r = composer.compose(
        OperationType.ADD_ITEM,
        product_status=ResolutionStatus.EXACT_MATCH,
        pending_blocking=True,
    )
    assert r is not None
    assert r.reason_code == "PENDING_RESOLUTION"


# --- Combinação N/A ---

def test_confirm_does_not_receive_missing_target(composer):
    """CONFIRM_ORDER não exige target: nunca gera MISSING_TARGET."""
    r = composer.compose(
        OperationType.CONFIRM_ORDER,
        target_status=TargetStatus.UNKNOWN,
    )
    assert r is None


def test_cancel_does_not_receive_missing_target(composer):
    r = composer.compose(
        OperationType.CANCEL_ORDER,
        target_status=TargetStatus.UNKNOWN,
    )
    assert r is None