import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from pipeline.semantic_intent_router import (
    SemanticIntent,
    MessageCategory,
    parse_semantic_intent,
    categorize,
    to_operation_type,
    to_query_type,
)
from order.resolved_operation import OperationType
from order.resolved_query import QueryType

_MODULE_PATH = (
    Path(__file__).parent.parent / "pipeline" / "semantic_intent_router.py"
)


@pytest.fixture(scope="module")
def router_source():
    return _MODULE_PATH.read_text(encoding="utf-8")


# =============================================
# SI-01..SI-09 — category routing
# =============================================

def test_si01_add_item_is_command():
    assert categorize(SemanticIntent.ADD_ITEM) is MessageCategory.COMMAND


def test_si02_remove_item_is_command():
    assert categorize(SemanticIntent.REMOVE_ITEM) is MessageCategory.COMMAND


def test_si03_change_quantity_is_command():
    assert categorize(SemanticIntent.CHANGE_QUANTITY) is MessageCategory.COMMAND


def test_si04_replace_item_is_command():
    assert categorize(SemanticIntent.REPLACE_ITEM) is MessageCategory.COMMAND


def test_si05_confirm_order_is_command():
    assert categorize(SemanticIntent.CONFIRM_ORDER) is MessageCategory.COMMAND


def test_si06_cancel_order_is_command():
    assert categorize(SemanticIntent.CANCEL_ORDER) is MessageCategory.COMMAND


def test_si07_query_price_is_query():
    assert categorize(SemanticIntent.QUERY_PRICE) is MessageCategory.QUERY


def test_si08_query_availability_is_query():
    assert categorize(SemanticIntent.QUERY_AVAILABILITY) is MessageCategory.QUERY


def test_si09_unknown_is_unknown():
    assert categorize(SemanticIntent.UNKNOWN) is MessageCategory.UNKNOWN


# =============================================
# SI-10..SI-12 — OperationType bridge
# =============================================

def test_si10_add_item_maps_to_operation_type():
    assert to_operation_type(SemanticIntent.ADD_ITEM) is OperationType.ADD_ITEM


def test_si11_query_price_has_no_operation_type():
    assert to_operation_type(SemanticIntent.QUERY_PRICE) is None


def test_si12_unknown_has_no_operation_type():
    assert to_operation_type(SemanticIntent.UNKNOWN) is None


# =============================================
# SI-13..SI-16 — QueryType bridge
# =============================================

def test_si13_query_price_maps_to_query_type():
    assert to_query_type(SemanticIntent.QUERY_PRICE) is QueryType.QUERY_PRICE


def test_si14_query_availability_maps_to_query_type():
    assert (
        to_query_type(SemanticIntent.QUERY_AVAILABILITY)
        is QueryType.QUERY_AVAILABILITY
    )


def test_si15_add_item_has_no_query_type():
    assert to_query_type(SemanticIntent.ADD_ITEM) is None


def test_si16_unknown_has_no_query_type():
    assert to_query_type(SemanticIntent.UNKNOWN) is None


# =============================================
# SI-17..SI-21 — closed-set parsing
# =============================================

def test_si17_exact_query_price_string_parses():
    assert parse_semantic_intent("QUERY_PRICE") is SemanticIntent.QUERY_PRICE


def test_si18_exact_query_availability_string_parses():
    assert (
        parse_semantic_intent("QUERY_AVAILABILITY")
        is SemanticIntent.QUERY_AVAILABILITY
    )


def test_si19_unknown_string_parses_to_unknown():
    assert (
        parse_semantic_intent("NOT_A_REAL_INTENT")
        is SemanticIntent.UNKNOWN
    )


def test_si20_natural_language_phrase_parses_to_unknown():
    assert parse_semantic_intent("quanto custa") is SemanticIntent.UNKNOWN


def test_si21_none_parses_to_unknown():
    assert parse_semantic_intent(None) is SemanticIntent.UNKNOWN


# =============================================
# Additional closed-set guarantees
# =============================================

def test_parsing_is_case_sensitive():
    """No case-folding — closed-set exact match."""
    assert parse_semantic_intent("query_price") is SemanticIntent.UNKNOWN
    assert parse_semantic_intent("Query_Price") is SemanticIntent.UNKNOWN


def test_parsing_rejects_non_string_values():
    assert parse_semantic_intent(42) is SemanticIntent.UNKNOWN
    assert parse_semantic_intent(object()) is SemanticIntent.UNKNOWN
    assert parse_semantic_intent([]) is SemanticIntent.UNKNOWN
    assert parse_semantic_intent({}) is SemanticIntent.UNKNOWN


def test_parsing_accepts_semantic_intent_instance_roundtrip():
    """Passing a SemanticIntent through the parser returns itself."""
    assert parse_semantic_intent("ADD_ITEM") is SemanticIntent.ADD_ITEM


def test_parsing_rejects_prefixed_or_decorated_strings():
    """No substrings, no prefixes, no trailing whitespace."""
    assert parse_semantic_intent(" QUERY_PRICE") is SemanticIntent.UNKNOWN
    assert parse_semantic_intent("QUERY_PRICE ") is SemanticIntent.UNKNOWN
    assert parse_semantic_intent("QUERY_PRICE\n") is SemanticIntent.UNKNOWN
    assert parse_semantic_intent("XQUERY_PRICE") is SemanticIntent.UNKNOWN


# =============================================
# SemanticIntent / category completeness
# =============================================

def test_semantic_intent_covers_contract_values():
    """Mirrors semantic contract v1.1.2 (9 intents)."""
    expected = {
        "ADD_ITEM", "REMOVE_ITEM", "CHANGE_QUANTITY",
        "REPLACE_ITEM", "QUERY_PRICE", "QUERY_AVAILABILITY",
        "CONFIRM_ORDER", "CANCEL_ORDER", "UNKNOWN",
    }
    actual = {i.name for i in SemanticIntent}
    assert actual == expected


def test_every_semantic_intent_has_a_category():
    """No intent may be missing from the category map."""
    for intent in SemanticIntent:
        cat = categorize(intent)
        assert cat in (
            MessageCategory.COMMAND,
            MessageCategory.QUERY,
            MessageCategory.UNKNOWN,
        )


def test_semantic_intent_is_not_operation_type():
    assert not issubclass(SemanticIntent, OperationType)
    assert not issubclass(OperationType, SemanticIntent)


def test_semantic_intent_is_not_query_type():
    assert not issubclass(SemanticIntent, QueryType)
    assert not issubclass(QueryType, SemanticIntent)


# =============================================
# Architectural isolation — no NLP, no engine, no state
# =============================================

def test_router_does_not_import_order_engine(router_source):
    import_re = re.compile(
        r"^\s*(?:from\s+order\.engine\s+import|import\s+order\.engine)",
        re.MULTILINE,
    )
    assert not import_re.search(router_source)


def test_router_does_not_import_order_state(router_source):
    import_re = re.compile(
        r"^\s*(?:from\s+order\.state\s+import|import\s+order\.state)",
        re.MULTILINE,
    )
    assert not import_re.search(router_source)


def test_router_does_not_import_catalog_retriever(router_source):
    import_re = re.compile(
        r"^\s*(?:from\s+order\.catalog_retriever\s+import|import\s+order\.catalog_retriever)",
        re.MULTILINE,
    )
    assert not import_re.search(router_source)


def test_router_does_not_import_product_resolver(router_source):
    import_re = re.compile(
        r"^\s*(?:from\s+order\.product_resolver\s+import|import\s+order\.product_resolver)",
        re.MULTILINE,
    )
    assert not import_re.search(router_source)


def test_router_does_not_import_operation_resolver(router_source):
    import_re = re.compile(
        r"^\s*(?:from\s+order\.operation_resolver\s+import|import\s+order\.operation_resolver)",
        re.MULTILINE,
    )
    assert not import_re.search(router_source)


def test_router_does_not_import_modular_adapter(router_source):
    import_re = re.compile(
        r"^\s*(?:from\s+benchmark\.adapters\.modular\s+import|import\s+benchmark\.adapters\.modular)",
        re.MULTILINE,
    )
    assert not import_re.search(router_source)


def test_router_does_not_import_ml_libraries(router_source):
    forbidden = ["gliner", "transformers", "torch", "sklearn", "numpy"]
    for lib in forbidden:
        pattern = re.compile(rf"^\s*(?:from\s+{lib}|import\s+{lib})", re.MULTILINE)
        assert not pattern.search(router_source), (
            f"router must not import {lib}"
        )


def test_router_does_not_import_resolution_pipeline(router_source):
    import_re = re.compile(
        r"^\s*(?:from\s+pipeline\.resolution_pipeline\s+import|import\s+pipeline\.resolution_pipeline)",
        re.MULTILINE,
    )
    assert not import_re.search(router_source)