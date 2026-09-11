import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from order.target import TargetType
from order.resolution_context import ResolutionContext
from order.pending import PendingResolution
from pipeline.reference_resolver import ReferenceResolver

def test_resolve_pending_with_brand():
    resolver = ReferenceResolver()
    pending = PendingResolution(product_term="provolone", candidates=["CQ-44", "CQ-46"])
    context = ResolutionContext(pending_resolution=pending)
    target = resolver.resolve("o da Tânia", context)
    assert target.type == TargetType.PENDING_ITEM
    assert target.brand_constraint == "Tânia"
    assert target.product_term == "provolone"

def test_resolve_pending_with_presentation():
    resolver = ReferenceResolver()
    pending = PendingResolution(product_term="emmental", candidates=["CQ-08", "CQ-09", "CQ-10"])
    context = ResolutionContext(pending_resolution=pending)
    target = resolver.resolve("em forma", context)
    assert target.type == TargetType.PENDING_ITEM
    assert target.presentation_constraint == "forma"

def test_resolve_change_operation():
    resolver = ReferenceResolver()
    context = ResolutionContext(active_item_id="item_1")
    target = resolver.resolve("na verdade são 8kg", context)
    assert target.type == TargetType.EXISTING_ITEM
    assert target.item_id == "item_1"

def test_resolve_unknown_no_evidence():
    resolver = ReferenceResolver()
    context = ResolutionContext()
    target = resolver.resolve("qualquer coisa", context)
    assert target.type == TargetType.UNKNOWN
    assert target.requires_clarification is True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])