import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from order.state import OrderState, OrderItem
from order.resolved_operation import OperationType
from order.resolution_composer import ResolutionComposer
from order.target_resolver import TargetResolver, TargetStatus
from order.product_resolver import ResolutionStatus


@pytest.fixture
def composer():
    return ResolutionComposer()


@pytest.fixture
def target_resolver():
    return TargetResolver()


@pytest.fixture
def state_provolone_e_manteiga():
    state = OrderState()
    state.add_item(OrderItem(product_term="Manteiga s/sal", product_id="CQ-29", quantity=10.0, unit="KG", resolved=True))
    state.add_item(OrderItem(product_term="Provolone Tânia", product_id="CQ-44", quantity=5.0, unit="KG", resolved=True))
    return state


# --- SOURCE ---

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


# --- DESTINATION ---

def test_replace_destination_not_found(composer):
    r = composer.compose(
        OperationType.REPLACE_ITEM,
        target_status=TargetStatus.RESOLVED,
        product_status=ResolutionStatus.NOT_FOUND,
    )
    assert r is not None
    assert r.reason_code == "MISSING_PRODUCT"


def test_replace_destination_ambiguous(composer):
    r = composer.compose(
        OperationType.REPLACE_ITEM,
        target_status=TargetStatus.RESOLVED,
        product_status=ResolutionStatus.AMBIGUOUS,
    )
    assert r is not None
    assert r.reason_code == "AMBIGUOUS_PRODUCT"


# --- BOTH OK ---

def test_replace_both_ok(composer):
    r = composer.compose(
        OperationType.REPLACE_ITEM,
        target_status=TargetStatus.RESOLVED,
        product_status=ResolutionStatus.EXACT_MATCH,
    )
    assert r is None


# --- BOTH PROBLEMATIC ---

def test_replace_both_unknown(composer):
    r = composer.compose(
        OperationType.REPLACE_ITEM,
        target_status=TargetStatus.UNKNOWN,
        product_status=ResolutionStatus.NOT_FOUND,
    )
    assert r is not None
    # Source failure takes precedence
    assert r.reason_code == "MISSING_TARGET"


def test_replace_both_ambiguous(composer):
    r = composer.compose(
        OperationType.REPLACE_ITEM,
        target_status=TargetStatus.AMBIGUOUS,
        product_status=ResolutionStatus.AMBIGUOUS,
    )
    assert r is not None
    assert r.reason_code == "AMBIGUOUS_TARGET"


# --- TARGET RESOLVER ---

def test_source_resolved_explicit(target_resolver, state_provolone_e_manteiga):
    result = target_resolver.resolve(
        "troca o provolone por gorgonzola",
        state_provolone_e_manteiga,
        reference_product_term="provolone",
    )
    assert result.status == TargetStatus.RESOLVED
    assert result.target_item_id == state_provolone_e_manteiga.items[1].id


def test_source_unknown_multiple_items(target_resolver, state_provolone_e_manteiga):
    """Last item sozinho NÃO autoriza source."""
    result = target_resolver.resolve(
        "troca uma por gorgonzola",
        state_provolone_e_manteiga,
        reference_product_term=None,
    )
    assert result.status == TargetStatus.UNKNOWN
    assert result.reason_code == "MISSING_TARGET"


def test_last_item_does_not_authorize_source(target_resolver, state_provolone_e_manteiga):
    """Mesmo com dois itens, sem referência, source é UNKNOWN."""
    result = target_resolver.resolve(
        "muda para 4",
        state_provolone_e_manteiga,
        reference_product_term=None,
    )
    assert result.status == TargetStatus.UNKNOWN


# --- ATOMICIDADE ---

def test_no_partial_operation_on_source_failure(composer):
    """Source UNKNOWN + destination OK → não retorna operação."""
    r = composer.compose(
        OperationType.REPLACE_ITEM,
        target_status=TargetStatus.UNKNOWN,
        product_status=ResolutionStatus.EXACT_MATCH,
    )
    assert r is not None
    assert r.outcome.value == "NEEDS_CLARIFICATION"


def test_no_partial_operation_on_destination_failure(composer):
    """Source OK + destination NOT_FOUND → não retorna operação."""
    r = composer.compose(
        OperationType.REPLACE_ITEM,
        target_status=TargetStatus.RESOLVED,
        product_status=ResolutionStatus.NOT_FOUND,
    )
    assert r is not None
    assert r.outcome.value == "NEEDS_CLARIFICATION"


# --- CONFIRM/CANCEL não afetados ---

def test_confirm_does_not_require_source_or_destination(composer):
    r = composer.compose(OperationType.CONFIRM_ORDER)
    assert r is None


def test_cancel_does_not_require_source_or_destination(composer):
    r = composer.compose(OperationType.CANCEL_ORDER)
    assert r is None