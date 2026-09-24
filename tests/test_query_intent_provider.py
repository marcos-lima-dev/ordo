import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from pipeline.query_intent_provider import (
    QueryIntentSignal,
    QueryIntentProvider,
)

_MODULE_PATH = (
    Path(__file__).parent.parent / "pipeline" / "query_intent_provider.py"
)


@pytest.fixture(scope="module")
def module_source():
    return _MODULE_PATH.read_text(encoding="utf-8")


# =============================================
# QIP-01 — Signal enum members
# =============================================

def test_qip01_signal_members_are_exactly_four():
    assert {s.name for s in QueryIntentSignal} == {
        "QUERY_PRICE",
        "QUERY_AVAILABILITY",
        "NOT_QUERY",
        "UNRESOLVED",
    }


def test_qip01b_signal_does_not_include_unknown():
    assert "UNKNOWN" not in {s.name for s in QueryIntentSignal}


def test_qip01c_signal_does_not_include_ambiguous():
    assert "AMBIGUOUS" not in {s.name for s in QueryIntentSignal}


def test_qip01d_signal_includes_unresolved():
    assert "UNRESOLVED" in {s.name for s in QueryIntentSignal}


# =============================================
# QIP-02 — Independence from SemanticIntent and MessageCategory
# =============================================

def test_qip02_signal_is_not_semantic_intent():
    from pipeline.semantic_intent_router import SemanticIntent
    assert not issubclass(QueryIntentSignal, SemanticIntent)
    assert not issubclass(SemanticIntent, QueryIntentSignal)


def test_qip02b_not_query_value_not_in_semantic_intent():
    from pipeline.semantic_intent_router import SemanticIntent
    si_values = {s.value for s in SemanticIntent}
    assert "NOT_QUERY" not in si_values


def test_qip02c_signal_is_not_message_category():
    from pipeline.semantic_intent_router import MessageCategory
    assert not issubclass(QueryIntentSignal, MessageCategory)


# =============================================
# QIP-03 — Abstract class cannot be instantiated
# =============================================

def test_qip03_provider_is_abstract():
    with pytest.raises(TypeError):
        QueryIntentProvider()


def test_qip03b_incomplete_subclass_raises():
    class Incomplete(QueryIntentProvider):
        pass

    with pytest.raises(TypeError):
        Incomplete()


# =============================================
# QIP-04 — Minimal implementation is substitutable
# =============================================

def test_qip04_minimal_implementation_returns_signal():
    class Fixed(QueryIntentProvider):
        def predict(self, message: str) -> QueryIntentSignal:
            return QueryIntentSignal.NOT_QUERY

    p = Fixed()
    assert p.predict("anything") is QueryIntentSignal.NOT_QUERY


def test_qip04b_substitutable_two_implementations():
    """Prove that two providers can sit behind the same contract."""

    class AlwaysPrice(QueryIntentProvider):
        def predict(self, message: str) -> QueryIntentSignal:
            return QueryIntentSignal.QUERY_PRICE

    class AlwaysAvailability(QueryIntentProvider):
        def predict(self, message: str) -> QueryIntentSignal:
            return QueryIntentSignal.QUERY_AVAILABILITY

    providers = [AlwaysPrice(), AlwaysAvailability()]
    results = [p.predict("x") for p in providers]
    assert results == [
        QueryIntentSignal.QUERY_PRICE,
        QueryIntentSignal.QUERY_AVAILABILITY,
    ]


# =============================================
# QIP-05 — Failure contract: exception, not signal
# =============================================

def test_qip05_provider_raises_operational_exception():
    class Broken(QueryIntentProvider):
        def predict(self, message: str) -> QueryIntentSignal:
            raise RuntimeError("model unavailable")

    with pytest.raises(RuntimeError, match="model unavailable"):
        Broken().predict("anything")


def test_qip05b_failure_does_not_return_signal():
    """A failing provider must not collapse to any signal value."""
    class Broken(QueryIntentProvider):
        def predict(self, message: str) -> QueryIntentSignal:
            raise RuntimeError("failure")

    p = Broken()
    try:
        result = p.predict("x")
    except RuntimeError:
        # accepted: exception path
        return
    # If we reach here, the implementation returned a value instead of raising.
    assert result not in QueryIntentSignal, (
        "provider returned a signal during operational failure"
    )


# =============================================
# QIP-06 — Dependency isolation
# =============================================

def test_qip06_does_not_import_order_engine(module_source):
    re_import = re.compile(
        r"^\s*(?:from\s+order\.engine\s+import|import\s+order\.engine)",
        re.MULTILINE,
    )
    assert not re_import.search(module_source)


def test_qip06b_does_not_import_order_state(module_source):
    re_import = re.compile(
        r"^\s*(?:from\s+order\.state\s+import|import\s+order\.state)",
        re.MULTILINE,
    )
    assert not re_import.search(module_source)


def test_qip06c_does_not_import_catalog_retriever(module_source):
    re_import = re.compile(
        r"^\s*(?:from\s+order\.catalog_retriever\s+import|import\s+order\.catalog_retriever)",
        re.MULTILINE,
    )
    assert not re_import.search(module_source)


def test_qip06d_does_not_import_product_resolver(module_source):
    re_import = re.compile(
        r"^\s*(?:from\s+order\.product_resolver\s+import|import\s+order\.product_resolver)",
        re.MULTILINE,
    )
    assert not re_import.search(module_source)


def test_qip06e_does_not_import_operation_resolver(module_source):
    re_import = re.compile(
        r"^\s*(?:from\s+order\.operation_resolver\s+import|import\s+order\.operation_resolver)",
        re.MULTILINE,
    )
    assert not re_import.search(module_source)


def test_qip06f_does_not_import_modular_adapter(module_source):
    re_import = re.compile(
        r"^\s*(?:from\s+benchmark\.adapters\.modular\s+import|import\s+benchmark\.adapters\.modular)",
        re.MULTILINE,
    )
    assert not re_import.search(module_source)


def test_qip06g_does_not_import_ml_libraries(module_source):
    for lib in ("gliner", "transformers", "torch", "sklearn", "numpy"):
        pattern = re.compile(
            rf"^\s*(?:from\s+{lib}\b|import\s+{lib}\b)",
            re.MULTILINE,
        )
        assert not pattern.search(module_source), (
            f"query_intent_provider.py must not import {lib}"
        )


def test_qip06h_does_not_import_semantic_intent_router(module_source):
    """
    The provider contract must not depend on SemanticIntent.
    The relation signal→intent is the caller's responsibility (T10-P9).
    """
    re_import = re.compile(
        r"^\s*(?:from\s+pipeline\.semantic_intent_router\s+import|import\s+pipeline\.semantic_intent_router)",
        re.MULTILINE,
    )
    assert not re_import.search(module_source)


def test_qip06i_does_not_import_resolution_pipeline(module_source):
    re_import = re.compile(
        r"^\s*(?:from\s+pipeline\.resolution_pipeline\s+import|import\s+pipeline\.resolution_pipeline)",
        re.MULTILINE,
    )
    assert not re_import.search(module_source)


def test_qip06j_does_not_import_query_resolution_pipeline(module_source):
    re_import = re.compile(
        r"^\s*(?:from\s+pipeline\.query_resolution_pipeline\s+import|import\s+pipeline\.query_resolution_pipeline)",
        re.MULTILINE,
    )
    assert not re_import.search(module_source)


# =============================================
# QIP-07 — Minimal surface
# =============================================

def test_qip07_provider_only_exposes_predict():
    """
    The provider must expose a minimal surface.
    Only `predict` should be public.
    """
    public_methods = [
        name
        for name in dir(QueryIntentProvider)
        if not name.startswith("_")
    ]
    assert "predict" in public_methods
    assert set(public_methods) == {"predict"}


# =============================================
# QIP-08 — T10-P10 semantics (NOT_QUERY is positive negative)
# =============================================

def test_qip08a_module_documents_t10p10(module_source):
    """The module must document T10-P10 as a frozen principle."""
    assert "T10-P10" in module_source
    assert "positive negative classification" in module_source.lower()


def test_qip08b_module_does_not_claim_not_query_is_uncertainty_fallback(module_source):
    """
    NOT_QUERY must not be documented as a fallback for uncertainty,
    subtype indecision, or operational failure.
    """
    lower = module_source.lower()
    # We reject the previously used wording.
    assert "cannot determine should return `not_query`" not in lower
    assert "cannot determine should return not_query" not in lower
    assert "not_query means the provider is uncertain" not in lower


def test_qip08c_enum_docstring_states_not_query_is_positive(module_source):
    """The enum-level docstring must reflect positive-negative semantics."""
    assert "positively classified" in module_source.lower() or (
        "positive negative" in module_source.lower()
    )


# =============================================
# QIP-09 — UNRESOLVED semantics (T10-P12 / T10-P13)
# =============================================

def test_qip09a_unresolved_exists():
    assert QueryIntentSignal.UNRESOLVED.name == "UNRESOLVED"
    assert QueryIntentSignal.UNRESOLVED.value == "UNRESOLVED"


def test_qip09b_unresolved_is_distinct_from_not_query():
    assert QueryIntentSignal.UNRESOLVED is not QueryIntentSignal.NOT_QUERY


def test_qip09c_unresolved_is_distinct_from_query_price():
    assert QueryIntentSignal.UNRESOLVED is not QueryIntentSignal.QUERY_PRICE


def test_qip09d_unresolved_is_distinct_from_query_availability():
    assert QueryIntentSignal.UNRESOLVED is not QueryIntentSignal.QUERY_AVAILABILITY


def test_qip09e_provider_can_return_unresolved_without_raising():
    """UNRESOLVED is a semantic outcome, not an operational failure."""
    class UnresolvedProvider(QueryIntentProvider):
        def predict(self, message: str) -> QueryIntentSignal:
            return QueryIntentSignal.UNRESOLVED

    p = UnresolvedProvider()
    assert p.predict("mensagem ambígua") is QueryIntentSignal.UNRESOLVED


def test_qip09f_unresolved_is_substitutable():
    class AlwaysUnresolved(QueryIntentProvider):
        def predict(self, message: str) -> QueryIntentSignal:
            return QueryIntentSignal.UNRESOLVED

    class AlwaysPrice(QueryIntentProvider):
        def predict(self, message: str) -> QueryIntentSignal:
            return QueryIntentSignal.QUERY_PRICE

    providers = [AlwaysUnresolved(), AlwaysPrice()]
    assert [p.predict("x") for p in providers] == [
        QueryIntentSignal.UNRESOLVED,
        QueryIntentSignal.QUERY_PRICE,
    ]


def test_qip09g_unresolved_not_in_semantic_intent():
    from pipeline.semantic_intent_router import SemanticIntent
    si_values = {s.value for s in SemanticIntent}
    assert "UNRESOLVED" not in si_values


def test_qip09h_unresolved_does_not_imply_exception():
    """
    A provider returning UNRESOLVED must not be interpreted as
    operational failure. The exception path is separate (QIP-05).
    """
    class UnresolvedProvider(QueryIntentProvider):
        def predict(self, message: str) -> QueryIntentSignal:
            return QueryIntentSignal.UNRESOLVED

    p = UnresolvedProvider()
    # Must not raise.
    result = p.predict("x")
    assert result is QueryIntentSignal.UNRESOLVED


# =============================================
# QIP-10 — T10-P11 / T10-P12 / T10-P13 documentation
# =============================================

def test_qip10a_module_documents_t10p11(module_source):
    assert "T10-P11" in module_source
    lower = module_source.lower()
    assert (
        "absence" in lower
        or "lack of" in lower
        or "insufficient" in lower
    )


def test_qip10b_module_documents_t10p12(module_source):
    assert "T10-P12" in module_source
    lower = module_source.lower()
    assert "unresolved" in lower
    assert "provider failure" in lower or "operational failure" in lower


def test_qip10c_module_documents_t10p13(module_source):
    assert "T10-P13" in module_source
    lower = module_source.lower()
    assert "unresolved" in lower
    assert "not_query" in lower
