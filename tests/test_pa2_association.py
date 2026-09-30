"""
PA-2 Validated Historical Association — Stage 1 tests.

Proves only the properties introduced in Stage 1:
    - factual storage and retrieval by opaque reference;
    - literal expression preservation;
    - provenance preservation;
    - multiplicity preservation (no silent deduplication);
    - reference isolation;
    - no message interpretation;
    - no authority imports.

Does not test applicability, compatibility, or authority.
Those remain deferred.
"""
import inspect
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from pipeline.pa2_association import (
    HistoricalAssociationRecord,
    PA2AssociationStore,
    InMemoryPA2AssociationStore,
)


def _rec(expr, pid, prov="clarification_1"):
    return HistoricalAssociationRecord(
        expression=expr,
        product_id=pid,
        clarification_provenance=prov,
    )


# ============================================
# Store retrieval shape
# ============================================

def test_pa2_store_lookup_empty():
    store = InMemoryPA2AssociationStore()
    assert store.lookup("unknown-ref") == ()


def test_pa2_store_lookup_single():
    store = InMemoryPA2AssociationStore()
    store.add("ref-1", _rec("queijo cereja", "CQ-10"))
    result = store.lookup("ref-1")
    assert len(result) == 1
    assert result[0].expression == "queijo cereja"
    assert result[0].product_id == "CQ-10"


def test_pa2_store_lookup_multiple():
    store = InMemoryPA2AssociationStore()
    store.add("ref-1", _rec("queijo cereja", "CQ-10"))
    store.add("ref-1", _rec("queijo cereja", "CQ-20"))
    store.add("ref-1", _rec("queijo cereja", "CQ-30"))
    result = store.lookup("ref-1")
    assert len(result) == 3
    assert {r.product_id for r in result} == {"CQ-10", "CQ-20", "CQ-30"}


# ============================================
# Reference isolation and multiplicity preservation
# ============================================

def test_pa2_store_reference_isolation():
    store = InMemoryPA2AssociationStore()
    store.add("ref-A", _rec("queijo cereja", "CQ-10"))
    store.add("ref-B", _rec("queijo cereja", "CQ-20"))
    assert store.lookup("ref-A")[0].product_id == "CQ-10"
    assert store.lookup("ref-B")[0].product_id == "CQ-20"
    assert store.lookup("ref-C") == ()


def test_pa2_store_does_not_deduplicate():
    store = InMemoryPA2AssociationStore()
    store.add("ref-1", _rec("queijo cereja", "CQ-10"))
    store.add("ref-1", _rec("queijo cereja", "CQ-10"))
    assert len(store.lookup("ref-1")) == 2


# ============================================
# Record invariants
# ============================================

def test_pa2_record_expression_literal():
    store = InMemoryPA2AssociationStore()
    store.add("ref-1", _rec("Queijo Cereja", "CQ-10"))
    assert store.lookup("ref-1")[0].expression == "Queijo Cereja"


def test_pa2_record_provenance_preserved():
    store = InMemoryPA2AssociationStore()
    rec = _rec("queijo cereja", "CQ-10", prov="clarification_xyz")
    store.add("ref-1", rec)
    assert store.lookup("ref-1")[0].clarification_provenance == "clarification_xyz"


def test_pa2_record_immutable():
    rec = _rec("queijo cereja", "CQ-10")
    with pytest.raises(FrozenInstanceError):
        rec.expression = "outro"


# ============================================
# No message interpretation
# ============================================

def test_pa2_store_no_message_param():
    sig = inspect.signature(InMemoryPA2AssociationStore.lookup)
    assert "message" not in sig.parameters


# ============================================
# Isolation — AST guards
# ============================================

def test_pa2_store_isolation():
    import pipeline.pa2_association as mod
    source = inspect.getsource(mod)
    forbidden = [
        "normalize_query",
        "CatalogRetriever",
        "ProductResolver",
        "OrderEngine",
        "command_execution",
    ]
    for name in forbidden:
        assert name not in source, f"must not reference {name}"


def test_pa2_no_authority_types():
    import pipeline.pa2_association as mod
    source = inspect.getsource(mod)
    forbidden = [
        "ResolutionResult",
        "pre_resolved_product_id",
        "execute_resolution",
        "to_resolved_operation",
    ]
    for name in forbidden:
        assert name not in source, f"must not reference {name}"