import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from order.state import OrderState, OrderItem
from order.pending import PendingResolution
from pipeline.reference_resolver import ReferenceResolver, ReferenceType


def test_resolve_pending_with_brand():
    resolver = ReferenceResolver()
    state = OrderState()
    state.add_item(OrderItem(product_term="provolone", quantity=5.0, unit="KG", resolved=False, needs_clarification=True))
    state.pending_resolution = PendingResolution(
        product_term="provolone",
        missing_fields=["brand"],
        reason="AMBIGUOUS",
    )
    signal = resolver.resolve("o da Tânia", state)
    assert signal.type == ReferenceType.PENDING_REFERENCE
    assert "brand" in signal.constraints


def test_resolve_pending_with_presentation():
    resolver = ReferenceResolver()
    state = OrderState()
    state.add_item(OrderItem(product_term="emmental", quantity=5.0, unit="KG", resolved=False, needs_clarification=True))
    state.pending_resolution = PendingResolution(
        product_term="emmental",
        missing_fields=["presentation"],
        reason="AMBIGUOUS",
    )
    signal = resolver.resolve("em forma", state)
    assert signal.type == ReferenceType.PENDING_REFERENCE
    assert "presentation" in signal.constraints


def test_resolve_change_operation():
    resolver = ReferenceResolver()
    state = OrderState()
    state.add_item(OrderItem(product_term="manteiga", quantity=10.0, unit="KG", resolved=True))
    signal = resolver.resolve("na verdade são 8kg", state)
    assert signal.type == ReferenceType.EXPLICIT_REFERENCE


def test_resolve_unknown_no_evidence():
    resolver = ReferenceResolver()
    state = OrderState()
    signal = resolver.resolve("qualquer coisa", state)
    assert signal.type == ReferenceType.UNKNOWN
    assert signal.requires_clarification is True