"""
Track C — Evidence Contract v0 tests.

Contract tests for the structured Evidence representation introduced
under P105. Tests verify that the new representation reproduces the
legacy substring classification for every provenance string currently
produced by CatalogRetriever, without changing any commercial decision.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from order.catalog_retriever import CatalogRetriever
from order.evidence import Evidence
from order.product_resolver import ProductResolver, ResolutionStatus


# =============================================
# Contract — Evidence fields
# =============================================

def test_evidence_is_frozen():
    ev = Evidence(sku="CQ-01", stream="ORIGINAL",
                  match_kind="ALIAS", match_strength="EXACT")
    with pytest.raises(Exception):
        ev.sku = "CQ-02"  # frozen dataclass


def test_evidence_alias_carries_source_and_approved():
    cat = CatalogRetriever()
    cands, prov = cat.retrieve_with_provenance("provolone de 5kg")
    assert "CQ-46" in prov
    for ev in prov["CQ-46"]:
        if ev.match_kind == "ALIAS":
            assert ev.source == "GENERATED"
            assert ev.approved is False


def test_evidence_name_has_no_alias_metadata():
    cat = CatalogRetriever()
    cands, prov = cat.retrieve_with_provenance("Grana 1/8")
    # NAME_EXACT on CQ-32, no alias fields
    names = [ev for ev in prov["CQ-32"] if ev.match_kind == "NAME"]
    assert names, "expected at least one NAME evidence for CQ-32"
    for ev in names:
        assert ev.source is None
        assert ev.approved is None


@pytest.mark.parametrize("legacy_input,expected_stream,expected_kind,expected_strength", [
    ("provolone de 5kg",  "ORIGINAL", "ALIAS", "EXACT"),   # ORIGINAL_ALIAS_EXACT
    ("provolone",         "ORIGINAL", "ALIAS", "TOKEN"),   # ORIGINAL_ALIAS_TOKEN
    ("Grana 1/8",         "ORIGINAL", "NAME",  "EXACT"),   # ORIGINAL_NAME_EXACT
])
def test_evidence_shape_matches_legacy(legacy_input, expected_stream,
                                       expected_kind, expected_strength):
    cat = CatalogRetriever()
    _, prov = cat.retrieve_with_provenance(legacy_input)
    flat = [ev for lst in prov.values() for ev in lst]
    assert any(
        ev.stream == expected_stream
        and ev.match_kind == expected_kind
        and ev.match_strength == expected_strength
        for ev in flat
    )


# =============================================
# P101 — same-SKU preservation
# =============================================

def test_p101_same_sku_positive_preserved_via_accumulation():
    """
    ORIGINAL produces positive evidence for a SKU; NORMALIZED also
    produces evidence for the same SKU. Both lists coexist; the
    positive evidence is not discarded.
    """
    cat = CatalogRetriever()
    _, prov = cat.retrieve_with_provenance("provolone de 5kg")
    # ORIGINAL produces ORIGINAL_ALIAS_EXACT for CQ-46
    cq46_evs = prov["CQ-46"]
    assert any(
        ev.stream == "ORIGINAL"
        and ev.match_kind == "ALIAS"
        and ev.match_strength == "EXACT"
        for ev in cq46_evs
    ), f"positive ORIGINAL evidence lost: {cq46_evs}"


# =============================================
# P102 — no manufacture
# =============================================

def test_p102_no_manufacture_from_aggregation():
    """
    A SKU that no stream matched with positive evidence must have
    NO positive Evidence after aggregation.
    """
    cat = CatalogRetriever()
    _, prov = cat.retrieve_with_provenance("provolone")
    for cid, evs in prov.items():
        for ev in evs:
            assert not (ev.match_strength == "EXACT"
                        and ev.match_kind in {"ALIAS", "NAME", "ORIGINAL_NAME"}), (
                f"{cid} got positive Evidence without a positive match: {ev}"
            )


# =============================================
# P103 — cross-SKU isolation
# =============================================

def test_p103_cross_sku_isolation():
    cat = CatalogRetriever()
    _, prov = cat.retrieve_with_provenance("provolone de 5kg")
    for cid, evs in prov.items():
        for ev in evs:
            assert ev.sku == cid, (
                f"evidence with sku={ev.sku} appeared in bucket {cid}"
            )


# =============================================
# P105 — representation ≠ authority
# =============================================

def test_p105_evidence_has_no_authority_field():
    ev = Evidence(sku="CQ-01", stream="ORIGINAL",
                  match_kind="ALIAS", match_strength="EXACT")
    # No 'authority', 'trust', 'positive', 'score', or 'rank' fields
    for forbidden in ("authority", "trust", "positive", "score", "rank", "priority"):
        assert not hasattr(ev, forbidden)


# =============================================
# Policy equivalence over real provenances
# =============================================

@pytest.mark.parametrize("query,expected_status", [
    # Tipo B: EXACT → AMBIGUOUS (2 candidates)
    ("provolone de 5kg",           ResolutionStatus.AMBIGUOUS),
    ("emmental 220g",              ResolutionStatus.AMBIGUOUS),
    ("gouda 220g",                 ResolutionStatus.AMBIGUOUS),
    ("manteiga com sal",           ResolutionStatus.AMBIGUOUS),
    ("manteiga sem sal",           ResolutionStatus.AMBIGUOUS),
    ("grana de 4kg",               ResolutionStatus.AMBIGUOUS),
    ("ricota de 500g",             ResolutionStatus.AMBIGUOUS),
    # Legitimate ambiguity: no positive
    ("provolone",                  ResolutionStatus.AMBIGUOUS),
])
def test_policy_equivalence_tipo_b_stays_ambiguous(query, expected_status):
    cat = CatalogRetriever()
    cands, prov = cat.retrieve_with_provenance(query)
    resolver = ProductResolver()
    status = resolver.resolve(cands, product_term=None, brand=None, evidence=prov)
    assert status == expected_status, (
        f"{query!r}: expected {expected_status}, got {status}; "
        f"candidates={cands}"
    )


@pytest.mark.parametrize("query,expected_status", [
    # Ambiguity legit / no positive anchor
    ("provolone",              ResolutionStatus.AMBIGUOUS),
    ("queijo cheddar bisnaga", ResolutionStatus.AMBIGUOUS),
])
def test_policy_equivalence_ambiguous_unchanged(query, expected_status):
    cat = CatalogRetriever()
    cands, prov = cat.retrieve_with_provenance(query)
    resolver = ProductResolver()
    status = resolver.resolve(cands, product_term=None, brand=None, evidence=prov)
    assert status == expected_status


# =============================================
# Legacy equivalence: string classification == evidence classification
# =============================================

_LEGACY_POSITIVE = {
    "ALIAS_EXACT", "NAME_EXACT", "ORIGINAL_EXACT",
    "APPROVED_ALIAS", "ENTITY_SIGNAL",
}


@pytest.mark.parametrize("legacy_str,should_be_positive", [
    ("ORIGINAL_ALIAS_EXACT",    True),
    ("ORIGINAL_NAME_EXACT",     True),
    ("ORIGINAL_ORIGINAL_EXACT", True),
    ("NORMALIZED_ALIAS_EXACT",  True),
    ("NORMALIZED_NAME_EXACT",   True),
    ("ORIGINAL_ALIAS_TOKEN",    False),
    ("ORIGINAL_ALIAS_SUBSET",   False),
    ("ORIGINAL_ALIAS_FUZZY",    False),
    ("NORMALIZED_ALIAS_TOKEN",  False),
    ("NORMALIZED_NAME_SUBSET",  False),
])
def test_legacy_string_classification_equivalence(legacy_str, should_be_positive):
    legacy_positive = any(src in legacy_str for src in _LEGACY_POSITIVE)

    # Reconstruct as Evidence
    parts = legacy_str.split("_", 1)  # stream + rest
    stream = parts[0]
    rest = parts[1]
    # rest is e.g. "ALIAS_EXACT" or "ORIGINAL_EXACT"
    if rest == "ORIGINAL_EXACT":
        kind, strength = "ORIGINAL_NAME", "EXACT"
    else:
        kind, strength = rest.rsplit("_", 1)

    ev = Evidence(sku="CQ-X", stream=stream, match_kind=kind, match_strength=strength)
    evidence_positive = ProductResolver._is_positive(ev)

    assert legacy_positive == evidence_positive, (
        f"{legacy_str}: legacy={legacy_positive} new={evidence_positive}"
    )
    assert legacy_positive == should_be_positive