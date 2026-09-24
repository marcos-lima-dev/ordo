import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from pipeline.query_intent_provider import (
    QueryIntentProvider,
    QueryIntentSignal,
)
from pipeline.query_intent_bootstrap import QueryIntentBootstrap

_MODULE_PATH = (
    Path(__file__).parent.parent
    / "pipeline"
    / "query_intent_bootstrap.py"
)


@pytest.fixture(scope="module")
def module_source():
    return _MODULE_PATH.read_text(encoding="utf-8")


@pytest.fixture
def bootstrap():
    return QueryIntentBootstrap()


# =============================================
# QIB-01 — contract conformance
# =============================================

def test_qib01_implements_query_intent_provider():
    assert issubclass(QueryIntentBootstrap, QueryIntentProvider)
    assert isinstance(QueryIntentBootstrap(), QueryIntentProvider)


def test_qib01b_returns_query_intent_signal(bootstrap):
    for msg in ["quanto custa o brie?", "tem brie?", "olá", "", "asdf"]:
        result = bootstrap.predict(msg)
        assert isinstance(result, QueryIntentSignal)


# =============================================
# QIB-02 — NOT_QUERY is a GAP for this bootstrap
# =============================================

def test_qib02_not_query_never_emitted(bootstrap):
    cases = [
        "olá",
        "bom dia",
        "",
        "   ",
        "asdkjfh",
        "valor",
        "tem provolone de quanto?",
        "quanto tem de provolone?",
        "qual o valor e tem disponível?",
    ]
    for msg in cases:
        assert bootstrap.predict(msg) is not QueryIntentSignal.NOT_QUERY


# =============================================
# QIB-03 — PRICE
# =============================================

@pytest.mark.parametrize(
    "msg",
    [
        "quanto custa o brie?",
        "Quanto custa o brie?",
        "qual o preço do provolone?",
        "qual o preco do provolone?",
        "preço?",
        "qual o valor do brie?",
        "qual o valor da mussarela?",
        "qual é o valor do brie?",
    ],
)
def test_qib03_price(bootstrap, msg):
    assert bootstrap.predict(msg) is QueryIntentSignal.QUERY_PRICE


# =============================================
# QIB-04 — AVAILABILITY
# =============================================

@pytest.mark.parametrize(
    "msg",
    [
        "tem brie?",
        "Tem brie?",
        "vocês têm provolone?",
        "voces tem provolone?",
        "tem disponível?",
        "tem disponivel?",
    ],
)
def test_qib04_availability(bootstrap, msg):
    assert bootstrap.predict(msg) is QueryIntentSignal.QUERY_AVAILABILITY


# =============================================
# QIB-05 — UNRESOLVED cases
# =============================================

@pytest.mark.parametrize(
    "msg",
    [
        "tem provolone de quanto?",
        "quanto tem de provolone?",
        "qual o valor e tem disponível?",
        "olá",
        "",
        "   ",
        "asdkjfh",
        "valor",
        "tem como?",
    ],
)
def test_qib05_unresolved(bootstrap, msg):
    assert bootstrap.predict(msg) is QueryIntentSignal.UNRESOLVED


# =============================================
# QIB-06 — T10-P14 (no COMMAND vocabulary)
# =============================================

def test_qib06_no_command_vocabulary_in_source(module_source):
    """
    The bootstrap source must not contain COMMAND vocabulary used as
    classification signals.

    Check is restricted to non-docstring string constants (regexes
    and comparison literals). Docstrings and comments are excluded,
    because T10-P14 forbids COMMAND *signals*, not Portuguese or
    English prose in documentation.
    """
    import ast

    tree = ast.parse(module_source)

    docstring_value_ids = set()
    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                docstring_value_ids.add(id(node.body[0].value))

    forbidden_tokens = (
        "manda",
        "adiciona",
        "remove",
        "troca",
        "confirma",
        "cancela",
    )

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstring_value_ids
        ):
            lower = node.value.lower()
            for token in forbidden_tokens:
                assert token not in lower, (
                    "non-docstring string contains COMMAND token "
                    f"{token!r}: {node.value!r}"
                )


def test_qib06b_command_message_resolved_by_query_rules_only(bootstrap):
    """
    'tem brie, manda dois' must resolve without any COMMAND knowledge.
    The comma is structural punctuation and carries no semantic weight
    (T10-P15). The strong AVAILABILITY evidence 'tem brie' is the only
    QUERY signal emitted. Expected: QUERY_AVAILABILITY.
    """
    assert (
        bootstrap.predict("tem brie, manda dois")
        is QueryIntentSignal.QUERY_AVAILABILITY
    )


# =============================================
# QIB-07 — dependency boundaries
# =============================================

def test_qib07_no_semantic_intent(module_source):
    assert "semantic_intent_router" not in module_source


def test_qib07b_no_resolution_pipeline(module_source):
    assert "resolution_pipeline" not in module_source
    assert "query_resolution_pipeline" not in module_source


def test_qib07c_no_order_state_or_engine(module_source):
    assert "order.state" not in module_source
    assert "order.engine" not in module_source


def test_qib07d_no_catalog_or_resolvers(module_source):
    assert "catalog_retriever" not in module_source
    assert "product_resolver" not in module_source
    assert "operation_resolver" not in module_source


def test_qib07e_no_ml_libraries(module_source):
    for lib in ("gliner", "transformers", "torch", "sklearn", "numpy"):
        pattern = re.compile(
            rf"^\s*(?:from\s+{lib}\b|import\s+{lib}\b)",
            re.MULTILINE,
        )
        assert not pattern.search(module_source), (
            f"query_intent_bootstrap.py must not import {lib}"
        )


# =============================================
# QIB-08 — determinism
# =============================================

def test_qib08_deterministic_single_case(bootstrap):
    msg = "quanto custa o brie?"
    results = {bootstrap.predict(msg) for _ in range(5)}
    assert results == {QueryIntentSignal.QUERY_PRICE}


def test_qib08b_deterministic_all_cases(bootstrap):
    for msg in [
        "tem brie?",
        "qual o valor do brie?",
        "tem provolone de quanto?",
        "olá",
    ]:
        first = bootstrap.predict(msg)
        for _ in range(3):
            assert bootstrap.predict(msg) is first


# =============================================
# QIB-09 — normalization is semantically equivalent
# =============================================

def test_qib09_case_insensitive(bootstrap):
    assert (
        bootstrap.predict("TEM BRIE?")
        is bootstrap.predict("tem brie?")
    )


def test_qib09b_accents_equivalent(bootstrap):
    assert (
        bootstrap.predict("vocês têm brie?")
        is bootstrap.predict("voces tem brie?")
    )


def test_qib09c_whitespace_equivalent(bootstrap):
    assert (
        bootstrap.predict("   tem   brie  ?  ")
        is bootstrap.predict("tem brie?")
    )


# =============================================
# QIB-10 — input is not mutated / type contract
# =============================================

def test_qib10_input_not_mutated(bootstrap):
    original = "  Quanto Custa o Brie?  "
    before = original
    bootstrap.predict(original)
    assert original == before


def test_qib10b_type_error_for_non_str(bootstrap):
    with pytest.raises(TypeError):
        bootstrap.predict(None)
    with pytest.raises(TypeError):
        bootstrap.predict(123)


# =============================================
# QIB-11 — T10-P15 (structural punctuation != semantic conflict)
# =============================================

@pytest.mark.parametrize(
    "msg,expected",
    [
        ("tem brie, manda dois", QueryIntentSignal.QUERY_AVAILABILITY),
        ("oi, tem brie?", QueryIntentSignal.QUERY_AVAILABILITY),
        (
            "bom dia, quanto custa o brie?",
            QueryIntentSignal.QUERY_PRICE,
        ),
        (
            "qual o preço do brie, por favor?",
            QueryIntentSignal.QUERY_PRICE,
        ),
    ],
)
def test_qib11_structural_punctuation_not_semantic_conflict(
    bootstrap, msg, expected
):
    assert bootstrap.predict(msg) is expected


def test_qib11b_comma_not_a_semantic_veto(module_source):
    """
    The bootstrap source must not treat comma as a semantic conflict
    flag (T10-P15).
    """
    assert "has_comma" not in module_source, (
        "bootstrap must not use a 'has_comma' semantic flag"
    )


def test_qib11c_price_plus_availability_still_unresolved(bootstrap):
    """
    T10-P15 does not change genuine QUERY-domain conflicts.
    """
    assert (
        bootstrap.predict("qual o valor e tem disponível?")
        is QueryIntentSignal.UNRESOLVED
    )