import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from order.state import OrderState, OrderItem
from order.target_resolver import TargetResolver, TargetStatus, TargetSource


@pytest.fixture
def resolver():
    return TargetResolver()


def test_dev02_token_overlap_single_match(resolver):
    """tira o provolone com 2 itens → match por token 'provolone'."""
    state = OrderState()
    state.add_item(OrderItem(product_term="Manteiga s/sal", quantity=10.0, unit="KG", resolved=True))
    state.add_item(OrderItem(product_term="Provolone Tânia", quantity=5.0, unit="KG", resolved=True))
    r = resolver.resolve(
        "tira o provolone",
        state,
        reference_product_term="tira o provolone",  # GLiNER ruidoso
    )
    # Não encontra na referência explícita, cai no passo 5 (token overlap)
    assert r.status == TargetStatus.RESOLVED
    assert r.source == TargetSource.MESSAGE_TOKEN_OVERLAP
    assert r.target_item_id == state.items[1].id


def test_dev10_multiple_items_ambiguous(resolver):
    """tira uma com 3 itens sem referência → AMBIGUOUS_TARGET."""
    state = OrderState()
    state.add_item(OrderItem(product_term="Manteiga s/sal", quantity=10.0, unit="KG", resolved=True))
    state.add_item(OrderItem(product_term="Provolone Tânia", quantity=5.0, unit="KG", resolved=True))
    state.add_item(OrderItem(product_term="Gorgonzola cartela", quantity=2.0, unit="KG", resolved=True))
    r = resolver.resolve("tira uma", state)
    assert r.status == TargetStatus.AMBIGUOUS
    assert r.reason_code == "AMBIGUOUS_TARGET"


def test_token_overlap_multiple_matches(resolver):
    """Dois provolones → AMBIGUOUS."""
    state = OrderState()
    state.add_item(OrderItem(product_term="Provolone Tânia", quantity=5.0, unit="KG", resolved=True))
    state.add_item(OrderItem(product_term="Provolone Riqueza", quantity=3.0, unit="KG", resolved=True))
    r = resolver.resolve("tira o provolone", state)
    assert r.status == TargetStatus.AMBIGUOUS
    assert r.reason_code == "AMBIGUOUS_TARGET"


def test_no_items_state(resolver):
    state = OrderState()
    r = resolver.resolve("tira o provolone", state)
    assert r.status == TargetStatus.UNKNOWN
    assert r.reason_code == "MISSING_TARGET"


def test_single_item_unique_match(resolver):
    state = OrderState()
    state.add_item(OrderItem(product_term="Manteiga s/sal", quantity=10.0, unit="KG", resolved=True))
    r = resolver.resolve("muda para 4", state)
    assert r.status == TargetStatus.RESOLVED
    assert r.source == TargetSource.UNIQUE_ORDER_ITEM_MATCH


def test_explicit_reference_priority(resolver):
    """Referência explícita tem prioridade sobre token overlap."""
    state = OrderState()
    state.add_item(OrderItem(product_term="Manteiga s/sal", quantity=10.0, unit="KG", resolved=True))
    state.add_item(OrderItem(product_term="Provolone Tânia", quantity=5.0, unit="KG", resolved=True))
    r = resolver.resolve("tira o provolone", state, reference_product_term="provolone")
    assert r.status == TargetStatus.RESOLVED
    assert r.source == TargetSource.EXPLICIT_ITEM_REFERENCE
    assert r.target_item_id == state.items[1].id