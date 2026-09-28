"""
Track A — same-SKU positive evidence preservation.

Uses the real catalog for characterization (Groups A, B, G) and a
stub retriever for structural invariants (Groups C, D, E, F).

Note: stub tests pass a query ("provolone") that survives
normalize_query, so the retriever's early-return on empty-normalized
does not short-circuit the stub.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from order.catalog_retriever import CatalogRetriever
from order.product_resolver import ProductResolver, ResolutionStatus


_CORPUS_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "track_a_evidence_preservation_corpus.json"
)
_CORPUS = json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))

_POSITIVE = ProductResolver.POSITIVE_EVIDENCE_SOURCES

# Query used for stub-based tests. Must survive normalize_query, i.e.
# be a single non-stopword token of length >= 3.
_STUB_QUERY = "provolone"


def _is_positive(prov: str) -> bool:
    return any(src in prov for src in _POSITIVE)


# =============================================
# Group A — same-SKU positive preservation (real catalog)
# =============================================

@pytest.mark.parametrize(
    "entry",
    _CORPUS["group_a_same_sku_positive_preservation"],
    ids=lambda e: e["input"],
)
def test_group_a_same_sku_positive_preservation(entry):
    cat = CatalogRetriever()
    cands, prov = cat.retrieve_with_provenance(entry["input"])
    sku = entry["positive_sku"]
    assert sku in prov, f"{sku} not in provenance: {prov}"
    assert _is_positive(prov[sku]), (
        f"expected positive provenance for {sku}, got {prov[sku]!r}"
    )


# =============================================
# Group B — no promotion
# =============================================

@pytest.mark.parametrize(
    "entry",
    _CORPUS["group_b_no_promotion"],
    ids=lambda e: e["input"],
)
def test_group_b_no_promotion(entry):
    cat = CatalogRetriever()
    cands, prov = cat.retrieve_with_provenance(entry["input"])
    for sku in entry["forbidden_positive"]:
        if sku in prov:
            assert not _is_positive(prov[sku]), (
                f"{sku} unexpectedly promoted to positive: {prov[sku]!r}"
            )


# =============================================
# Group G — legitimate ambiguity
# =============================================

@pytest.mark.parametrize(
    "entry",
    _CORPUS["group_g_legitimate_ambiguity"],
    ids=lambda e: e["input"],
)
def test_group_g_legitimate_ambiguity(entry):
    cat = CatalogRetriever()
    cands, prov = cat.retrieve_with_provenance(entry["input"])
    assert len(cands) >= entry["min_candidates"]
    resolver = ProductResolver()
    status = resolver.resolve(cands, product_term=None, brand=None, evidence=prov)
    assert status == ResolutionStatus.AMBIGUOUS


# =============================================
# Stub retriever for structural invariants
# =============================================

class _StubRetriever(CatalogRetriever):
    """Bypasses __init__; injects canned _retrieve_core outputs."""
    def __init__(self, orig, norm):
        self._orig = orig
        self._norm = norm

    def _retrieve_core(self, query, source):
        return self._orig if source == "ORIGINAL" else self._norm


# =============================================
# Group C — cross-SKU: no evidence bleed
# =============================================

def test_group_c_cross_sku_no_bleed():
    stub = _StubRetriever(
        (["CQ-46"], {"CQ-46": "ORIGINAL_ALIAS_EXACT"}),
        (["CQ-44"], {"CQ-44": "NORMALIZED_ALIAS_EXACT"}),
    )
    cands, prov = stub.retrieve_with_provenance(_STUB_QUERY)
    assert set(cands) == {"CQ-44", "CQ-46"}
    assert _is_positive(prov["CQ-44"])
    assert _is_positive(prov["CQ-46"])


def test_group_c_cross_sku_no_downgrade():
    stub = _StubRetriever(
        (["CQ-44"], {"CQ-44": "ORIGINAL_ALIAS_EXACT"}),
        (["CQ-44"], {"CQ-44": "NORMALIZED_ALIAS_TOKEN"}),
    )
    cands, prov = stub.retrieve_with_provenance(_STUB_QUERY)
    assert prov["CQ-44"] == "ORIGINAL_ALIAS_EXACT"
    assert _is_positive(prov["CQ-44"])


# =============================================
# Group D — multiple EXACT, resolver stays ambiguous
# =============================================

def test_group_d_multiple_exact_resolver_ambiguous():
    stub = _StubRetriever(
        (["CQ-A"], {"CQ-A": "ORIGINAL_ALIAS_EXACT"}),
        (["CQ-B"], {"CQ-B": "NORMALIZED_ALIAS_EXACT"}),
    )
    cands, prov = stub.retrieve_with_provenance(_STUB_QUERY)
    assert set(cands) == {"CQ-A", "CQ-B"}
    resolver = ProductResolver()
    status = resolver.resolve(cands, product_term=None, brand=None, evidence=prov)
    assert status == ResolutionStatus.AMBIGUOUS


# =============================================
# Group E — ORIGINAL only
# =============================================

def test_group_e_original_only_exact_unchanged():
    stub = _StubRetriever(
        (["CQ-X"], {"CQ-X": "ORIGINAL_ALIAS_EXACT"}),
        ([], {}),
    )
    cands, prov = stub.retrieve_with_provenance(_STUB_QUERY)
    assert cands == ["CQ-X"]
    assert prov["CQ-X"] == "ORIGINAL_ALIAS_EXACT"


def test_group_e_original_only_non_positive_unchanged():
    stub = _StubRetriever(
        (["CQ-X"], {"CQ-X": "ORIGINAL_ALIAS_TOKEN"}),
        ([], {}),
    )
    cands, prov = stub.retrieve_with_provenance(_STUB_QUERY)
    assert prov["CQ-X"] == "ORIGINAL_ALIAS_TOKEN"


# =============================================
# Group F — NORMALIZED only
# =============================================

def test_group_f_normalized_only_unchanged():
    stub = _StubRetriever(
        ([], {}),
        (["CQ-Y"], {"CQ-Y": "NORMALIZED_ALIAS_EXACT"}),
    )
    cands, prov = stub.retrieve_with_provenance(_STUB_QUERY)
    assert cands == ["CQ-Y"]
    assert prov["CQ-Y"] == "NORMALIZED_ALIAS_EXACT"


# =============================================
# Corpus shape
# =============================================

def test_corpus_frozen_before_implementation():
    assert _CORPUS.get("frozen_before_implementation") is True


def test_corpus_checkpoint():
    assert _CORPUS["checkpoint"] == "e035890e30c72732ab27f7cd573cd239ef6b93d1"