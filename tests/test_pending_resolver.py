import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from order.state import OrderState, OrderItem
from order.pending import PendingResolution
from order.pending_resolver import PendingResolver, PendingStatus
from order.catalog_retriever import CatalogRetriever


@pytest.fixture
def retriever():
    return CatalogRetriever()

@pytest.fixture
def resolver():
    return PendingResolver()


def test_no_pending_not_applicable(resolver, retriever):
    state = OrderState()
    semantic_signals = {"intent": "ADD_ITEM", "explicit_brand": "Tânia"}
    result = resolver.resolve("da Tânia", state, semantic_signals, retriever)
    assert result.status == PendingStatus.NOT_APPLICABLE


def test_pending_brand_unique_candidate(resolver, retriever):
    state = OrderState()
    state.pending_resolution = PendingResolution(
        product_term="provolone",
        quantity=5.0,
        unit="KG",
        missing_fields=["brand"],
        reason="AMBIGUOUS",
    )
    semantic_signals = {
        "intent": "ADD_ITEM",
        "product_term": None,
        "explicit_brand": "da Tânia",
        "explicit_presentation": None,
    }
    result = resolver.resolve("da Tânia", state, semantic_signals, retriever)
    assert result.status == PendingStatus.RESOLVED
    assert result.resolved_product_id == "CQ-44"


def test_pending_brand_multiple_candidates(resolver, retriever):
    state = OrderState()
    state.pending_resolution = PendingResolution(
        product_term="gorgonzola",
        missing_fields=["brand"],
        reason="AMBIGUOUS",
    )
    semantic_signals = {
        "intent": "ADD_ITEM",
        "product_term": None,
        "explicit_brand": "São Vicente",
        "explicit_presentation": None,
    }
    result = resolver.resolve("São Vicente", state, semantic_signals, retriever)
    assert result.status == PendingStatus.AMBIGUOUS
    assert result.reason_code == "AMBIGUOUS_PRODUCT"


def test_pending_brand_no_candidate(resolver, retriever):
    state = OrderState()
    state.pending_resolution = PendingResolution(
        product_term="manteiga",
        missing_fields=["brand"],
        reason="AMBIGUOUS",
    )
    semantic_signals = {
        "intent": "ADD_ITEM",
        "product_term": None,
        "explicit_brand": "Tânia",
        "explicit_presentation": None,
    }
    result = resolver.resolve("da Tânia", state, semantic_signals, retriever)
    assert result.status == PendingStatus.INCOMPATIBLE


def test_pending_presentation_candidate(resolver, retriever):
    state = OrderState()
    state.pending_resolution = PendingResolution(
        product_term="gorgonzola",
        missing_fields=["presentation"],
        reason="AMBIGUOUS",
    )
    semantic_signals = {
        "intent": "ADD_ITEM",
        "product_term": None,
        "explicit_brand": None,
        "explicit_presentation": "forma",
    }
    result = resolver.resolve("em forma", state, semantic_signals, retriever)
    assert result.status == PendingStatus.RESOLVED


def test_preserves_quantity_unit(resolver, retriever):
    state = OrderState()
    state.pending_resolution = PendingResolution(
        product_term="provolone",
        quantity=7.0,
        unit="KG",
        missing_fields=["brand"],
        reason="AMBIGUOUS",
    )
    semantic_signals = {
        "intent": "ADD_ITEM",
        "product_term": None,
        "explicit_brand": "Tânia",
    }
    result = resolver.resolve("da Tânia", state, semantic_signals, retriever)
    assert result.status == PendingStatus.RESOLVED
    assert result.updated_pending.quantity == 7.0
    assert result.updated_pending.unit == "KG"


def test_does_not_mutate_original_pending(resolver, retriever):
    state = OrderState()
    original = PendingResolution(
        product_term="provolone",
        quantity=5.0,
        unit="KG",
        missing_fields=["brand"],
        reason="AMBIGUOUS",
    )
    state.pending_resolution = original
    semantic_signals = {
        "intent": "ADD_ITEM",
        "product_term": None,
        "explicit_brand": "Tânia",
    }
    resolver.resolve("da Tânia", state, semantic_signals, retriever)
    # Original não foi modificado
    assert original.brand is None
    assert "brand" in original.missing_fields


def test_new_operation_not_absorbed(resolver, retriever):
    state = OrderState()
    state.pending_resolution = PendingResolution(
        product_term="provolone",
        missing_fields=["brand"],
    )
    semantic_signals = {
        "intent": "ADD_ITEM",
        "product_term": "manteiga",
        "explicit_brand": None,
    }
    result = resolver.resolve(
        "coloca também 2kg de manteiga", state, semantic_signals, retriever
    )
    assert result.status == PendingStatus.NOT_APPLICABLE


def test_incompatible_intent_not_absorbed(resolver, retriever):
    state = OrderState()
    state.pending_resolution = PendingResolution(
        product_term="provolone",
        missing_fields=["brand"],
    )
    semantic_signals = {
        "intent": "REMOVE_ITEM",
        "product_term": None,
        "explicit_brand": "Tânia",
    }
    result = resolver.resolve("tira da Tânia", state, semantic_signals, retriever)
    assert result.status == PendingStatus.NOT_APPLICABLE