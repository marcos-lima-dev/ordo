import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from order.state import OrderState, OrderItem
from order.target_resolver import TargetResolver, TargetStatus, TargetSource
from order.pending import PendingResolution


@pytest.fixture
def state_two_items():
    state = OrderState()
    state.add_item(OrderItem(product_term="Manteiga s/sal", quantity=10.0, unit="KG", resolved=True))
    state.add_item(OrderItem(product_term="Provolone Tânia", quantity=5.0, unit="KG", resolved=True))
    return state


@pytest.fixture
def state_one_item():
    state = OrderState()
    state.add_item(OrderItem(product_term="Manteiga s/sal", quantity=10.0, unit="KG", resolved=True))
    return state


@pytest.fixture
def state_three_items():
    state = OrderState()
    state.add_item(OrderItem(product_term="Manteiga s/sal", quantity=10.0, unit="KG", resolved=True))
    state.add_item(OrderItem(product_term="Provolone Tânia", quantity=5.0, unit="KG", resolved=True))
    state.add_item(OrderItem(product_term="Gorgonzola cartela", quantity=2.0, unit="KG", resolved=True))
    return state


def test_explicit_reference_single_match(state_two_items):
    resolver = TargetResolver()
    result = resolver.resolve("tira o provolone", state_two_items, reference_product_term="provolone")
    assert result.status == TargetStatus.RESOLVED
    assert result.source == TargetSource.EXPLICIT_ITEM_REFERENCE
    assert result.target_item_id == state_two_items.items[1].id


def test_explicit_reference_multiple_matches():
    state = OrderState()
    state.add_item(OrderItem(product_term="Provolone Tânia", quantity=5.0, unit="KG", resolved=True))
    state.add_item(OrderItem(product_term="Provolone Riqueza", quantity=3.0, unit="KG", resolved=True))
    resolver = TargetResolver()
    result = resolver.resolve("tira o provolone", state, reference_product_term="provolone")
    assert result.status == TargetStatus.AMBIGUOUS
    assert result.reason_code == "AMBIGUOUS_TARGET"


def test_explicit_reference_no_match(state_two_items):
    resolver = TargetResolver()
    result = resolver.resolve("tira o gorgonzola", state_two_items, reference_product_term="gorgonzola")
    # Cai no fluxo seguinte (não encontrou match explícito)
    assert result.status in [TargetStatus.AMBIGUOUS, TargetStatus.UNKNOWN]


def test_generic_reference_single_item(state_one_item):
    resolver = TargetResolver()
    result = resolver.resolve("tira esse", state_one_item)
    assert result.status == TargetStatus.RESOLVED
    assert result.source == TargetSource.CONTEXTUAL_REFERENCE


def test_generic_reference_multiple_items(state_three_items):
    resolver = TargetResolver()
    result = resolver.resolve("tira esse", state_three_items)
    assert result.status == TargetStatus.AMBIGUOUS
    assert result.reason_code == "AMBIGUOUS_TARGET"


def test_unique_order_item_match(state_one_item):
    resolver = TargetResolver()
    result = resolver.resolve("muda para 4", state_one_item)
    assert result.status == TargetStatus.RESOLVED
    assert result.source == TargetSource.UNIQUE_ORDER_ITEM_MATCH


def test_last_item_does_not_authorize_target(state_three_items):
    """Last item sozinho NÃO autoriza target. Com múltiplos itens → AMBIGUOUS."""
    resolver = TargetResolver()
    result = resolver.resolve("muda para 4", state_three_items)
    assert result.status == TargetStatus.AMBIGUOUS
    assert result.reason_code == "AMBIGUOUS_TARGET"
    assert result.target_item_id is None


def test_pending_reference_single_match():
    state = OrderState()
    state.add_item(OrderItem(product_term="provolone", quantity=5.0, unit="KG", resolved=False, needs_clarification=True))
    state.pending_resolution = PendingResolution(product_term="provolone", missing_fields=["brand"], reason="AMBIGUOUS")
    resolver = TargetResolver()
    result = resolver.resolve("da Tânia", state)
    assert result.status == TargetStatus.RESOLVED
    assert result.source == TargetSource.PENDING_REFERENCE


def test_no_evidence_unknown(state_three_items):
    """Múltiplos itens sem referência → AMBIGUOUS."""
    resolver = TargetResolver()
    result = resolver.resolve("muda para 4", state_three_items)
    assert result.status == TargetStatus.AMBIGUOUS
    assert result.reason_code == "AMBIGUOUS_TARGET"


def test_confirm_order_does_not_require_target(state_two_items):
    """TargetResolver puro não conhece a operação; múltiplos itens → AMBIGUOUS.
    O pipeline não chama TargetResolver para CONFIRM_ORDER."""
    resolver = TargetResolver()
    result = resolver.resolve("pode fechar", state_two_items)
    assert result.status == TargetStatus.AMBIGUOUS


def test_cancel_order_does_not_require_target(state_two_items):
    """Mesmo raciocínio do CONFIRM_ORDER."""
    resolver = TargetResolver()
    result = resolver.resolve("cancela tudo", state_two_items)
    assert result.status == TargetStatus.AMBIGUOUS