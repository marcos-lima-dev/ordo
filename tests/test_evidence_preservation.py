# imports
from order.evidence import Evidence
from order.catalog_retriever import CatalogRetriever
from order.product_resolver import ProductResolver, ResolutionStatus


# Legacy string → (stream, kind, strength).
_LEGACY_TO_EVIDENCE = {
    "ORIGINAL_ALIAS_EXACT":    ("ORIGINAL",   "ALIAS",         "EXACT"),
    "ORIGINAL_ALIAS_TOKEN":    ("ORIGINAL",   "ALIAS",         "TOKEN"),
    "ORIGINAL_ALIAS_SUBSET":   ("ORIGINAL",   "ALIAS",         "SUBSET"),
    "ORIGINAL_ALIAS_FUZZY":    ("ORIGINAL",   "ALIAS",         "FUZZY"),
    "ORIGINAL_NAME_EXACT":     ("ORIGINAL",   "NAME",          "EXACT"),
    "ORIGINAL_NAME_TOKEN":     ("ORIGINAL",   "NAME",          "TOKEN"),
    "ORIGINAL_NAME_SUBSET":    ("ORIGINAL",   "NAME",          "SUBSET"),
    "ORIGINAL_ORIGINAL_EXACT": ("ORIGINAL",   "ORIGINAL_NAME", "EXACT"),
    "NORMALIZED_ALIAS_EXACT":    ("NORMALIZED", "ALIAS",         "EXACT"),
    "NORMALIZED_ALIAS_TOKEN":    ("NORMALIZED", "ALIAS",         "TOKEN"),
    "NORMALIZED_ALIAS_SUBSET":   ("NORMALIZED", "ALIAS",         "SUBSET"),
    "NORMALIZED_ALIAS_FUZZY":    ("NORMALIZED", "ALIAS",         "FUZZY"),
    "NORMALIZED_NAME_EXACT":     ("NORMALIZED", "NAME",          "EXACT"),
    "NORMALIZED_NAME_TOKEN":     ("NORMALIZED", "NAME",          "TOKEN"),
    "NORMALIZED_NAME_SUBSET":    ("NORMALIZED", "NAME",          "SUBSET"),
    "NORMALIZED_ORIGINAL_EXACT": ("NORMALIZED", "ORIGINAL_NAME", "EXACT"),
}


def _legacy_str_to_evidence(cid: str, legacy: str) -> Evidence:
    stream, kind, strength = _LEGACY_TO_EVIDENCE[legacy]
    return Evidence(sku=cid, stream=stream,
                    match_kind=kind, match_strength=strength)


def _is_positive(ev_list) -> bool:
    return any(
        ev.match_strength == "EXACT"
        and ev.match_kind in {"ALIAS", "NAME", "ORIGINAL_NAME"}
        for ev in ev_list
    )


class _StubRetriever(CatalogRetriever):
    """Bypasses __init__; injects canned _retrieve_core outputs (legacy strings)."""
    def __init__(self, orig, norm):
        self._orig = orig
        self._norm = norm

    def _retrieve_core(self, query, source):
        raw = self._orig if source == "ORIGINAL" else self._norm
        cands, prov = raw
        evidence = {cid: [_legacy_str_to_evidence(cid, s)]
                    for cid, s in prov.items()}
        return cands, evidence