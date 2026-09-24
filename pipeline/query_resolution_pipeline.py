"""
ORDO — Query Resolution Pipeline (Track 10, Stage 4C).

Resolves a semantic QUERY intent into a QueryResolutionResult by
reusing the canonical CatalogRetriever + ProductResolver path.

T10-P8 — RECOGNITION ≠ RESOLUTION:
    Recognition (upstream, not in this module) determines WHAT the user
    is asking.
    Query Resolution (this module) determines WHICH domain entity the
    recognized query refers to.

Precondition:
    `semantic_intent` MUST belong to MessageCategory.QUERY, i.e. it
    must be one of:
        SemanticIntent.QUERY_PRICE
        SemanticIntent.QUERY_AVAILABILITY
    Passing a COMMAND or UNKNOWN intent is API misuse and raises
    ValueError.

State isolation:
    NO OrderState. NO OrderEngine. NO execute_resolution.
    NO PendingResolver. The absence of `state` in the signature makes
    T10-P3 structural.

Product signals:
    The adapter is used only to extract `product_term`, `explicit_brand`,
    and `explicit_presentation` from the message. Its `intent`,
    `product_resolution_status`, and `catalog_candidates` are NOT
    authoritative for query routing/resolution.

Product resolution:
    Retrieval and product resolution are executed explicitly here, with
    provenance coupled to the ProductResolver decision, mirroring the
    COMMAND pipeline's safety pattern.

Mapping (frozen for Stage 4C):
    EXACT_MATCH       → QueryResolutionStatus.RESOLVED (with product_id)
    AMBIGUOUS         → QueryResolutionStatus.NEEDS_CLARIFICATION
    NOT_FOUND         → QueryResolutionStatus.PRODUCT_NOT_FOUND
    HIGH_CONFIDENCE   → NOT AUTHORIZED (RuntimeError if observed)
    anything else     → RuntimeError (never silently handled)

Evidence:
    Real provenance from `retrieve_with_provenance` is carried into
    `QueryResolutionResult.evidence`. No fabricated evidence.
    The boundary (Stage 3) intentionally does NOT propagate this
    evidence into `ResolvedQuery.evidence`.
"""
from benchmark.adapters.modular import ModularAdapter
from order.catalog_retriever import CatalogRetriever
from order.product_resolver import ProductResolver
from order.query_resolution_result import (
    QueryResolutionResult,
    QueryResolutionStatus,
)
from pipeline.semantic_intent_router import SemanticIntent, to_query_type


# =============================================
# Lazy singletons (mirrors pipeline/resolution_pipeline.py)
# =============================================

_adapter = None
_catalog_retriever = None
_product_resolver = None


def _get_adapter():
    global _adapter
    if _adapter is None:
        _adapter = ModularAdapter()
    return _adapter


def _get_catalog_retriever():
    global _catalog_retriever
    if _catalog_retriever is None:
        _catalog_retriever = CatalogRetriever()
    return _catalog_retriever


def _get_product_resolver():
    global _product_resolver
    if _product_resolver is None:
        _product_resolver = ProductResolver()
    return _product_resolver


# =============================================
# Public API
# =============================================

def resolve_query(
    message: str,
    semantic_intent: SemanticIntent,
) -> QueryResolutionResult:
    """
    Resolves a QUERY semantic intent into a QueryResolutionResult.

    Precondition: `semantic_intent` must be a QUERY intent
    (QUERY_PRICE or QUERY_AVAILABILITY). Any other intent is API misuse
    and raises ValueError.

    Deterministic. No OrderState. No OrderEngine. No PendingResolver.

    See module docstring for the full contract.
    """
    # Precondition: must be a QUERY semantic intent.
    query_type = to_query_type(semantic_intent)
    if query_type is None:
        raise ValueError(
            f"resolve_query requires a QUERY semantic intent; "
            f"got {semantic_intent.name}"
        )

    adapter = _get_adapter()
    catalog_retriever = _get_catalog_retriever()
    product_resolver = _get_product_resolver()

    # Adapter is used only for product signals (see module docstring).
    interpretation = adapter.predict(message)
    product_term = interpretation.get("product_term")
    brand = interpretation.get("explicit_brand")
    presentation = interpretation.get("explicit_presentation")

    # Explicit retrieval + resolution, coupling provenance to the
    # ProductResolver decision (mirrors COMMAND pipeline).
    candidates, provenance = catalog_retriever.retrieve_with_provenance(
        message, brand=brand, presentation=presentation
    )
    product_status = product_resolver.resolve(
        candidates,
        product_term=product_term,
        brand=brand,
        evidence=provenance,
    )

    # Real evidence only. Deterministic ordering, association preserved.
    evidence_list = [
        f"{cid}:{src}" for cid, src in sorted(provenance.items())
    ]

    if product_status == "EXACT_MATCH":
        if len(candidates) != 1:
            # Defensive: ProductResolver should not emit EXACT_MATCH
            # for more than one candidate.
            raise RuntimeError(
                f"ProductResolver returned EXACT_MATCH with "
                f"{len(candidates)} candidates; expected exactly 1."
            )
        return QueryResolutionResult(
            status=QueryResolutionStatus.RESOLVED,
            query_type=query_type,
            product_id=candidates[0],
            evidence=evidence_list,
        )

    if product_status == "AMBIGUOUS":
        return QueryResolutionResult(
            status=QueryResolutionStatus.NEEDS_CLARIFICATION,
            query_type=query_type,
            product_id=None,
            reason_code="AMBIGUOUS_PRODUCT",
            evidence=evidence_list,
        )

    if product_status == "NOT_FOUND":
        return QueryResolutionResult(
            status=QueryResolutionStatus.PRODUCT_NOT_FOUND,
            query_type=query_type,
            product_id=None,
            reason_code="PRODUCT_NOT_FOUND",
            evidence=evidence_list,
        )

    if product_status == "HIGH_CONFIDENCE":
        # Track 10 Stage 4C: NOT AUTHORIZED. This stage does not
        # decide how HIGH_CONFIDENCE maps. If observed, STOP and report.
        raise RuntimeError(
            "ProductResolver returned HIGH_CONFIDENCE, which is NOT "
            "AUTHORIZED in Track 10 Stage 4C. STOP and report to the "
            "Tech Lead before deciding a mapping."
        )

    # Any other status is unexpected — never silently handled.
    raise RuntimeError(
        f"Unexpected ProductResolver status: {product_status!r}"
    )