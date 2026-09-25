"""
ORDO — Track 10, Stage 4I.4a.

Characterization freeze for ModularAdapter._classify_intent.

This file is test-only. It does NOT modify production code. It
bypasses ModularAdapter.__init__ to avoid loading GLiNER,
transformers, CatalogRetriever, or ProductResolver, and exercises
only _classify_intent.

Purpose: freeze the observed legacy behavior BEFORE introducing
the fresh CommandRecognizer in Stage 4I.4b.

T10-P36: differences required by the new recognizer contract will
be documented and tested explicitly in later stages. This file
only records what exists today.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from benchmark.adapters.modular import ModularAdapter


_CORPUS_PATH = (
    Path(__file__).parent / "fixtures" / "command_recognizer_v1_corpus.json"
)


@pytest.fixture(scope="module")
def corpus():
    return json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))


# =============================================
# Characterization harness
# =============================================

def _make_adapter_without_init():
    """
    Test-only harness. Bypasses ModularAdapter.__init__ so that no
    heavy dependency is loaded. Only _classify_intent is exercised.
    """
    return object.__new__(ModularAdapter)


def _install_legacy_state(adapter, classifier=None):
    adapter.intent_classifier = classifier
    adapter.intent_label_map = {
        "LABEL_0": "ADD_ITEM",
        "LABEL_1": "REMOVE_ITEM",
        "LABEL_2": "CHANGE_QUANTITY",
        "LABEL_3": "CONFIRM_ORDER",
        "LABEL_4": "CANCEL_ORDER",
        "LABEL_5": "UNKNOWN",
    }


def _fake_classifier(label):
    def callable_(message):
        return [{"label": label, "score": 1.0}]
    return callable_


def _raising_classifier(message):
    raise RuntimeError("characterization: classifier failure")


# =============================================
# CFR-01 — fallback corpus (intent_classifier = None)
# =============================================

def test_cfr01_fallback_corpus(corpus):
    adapter = _make_adapter_without_init()
    _install_legacy_state(adapter, classifier=None)

    for case in corpus["fallback_cases"]:
        got = adapter._classify_intent(case["input"])
        assert got == case["legacy_output"], (
            f"[{case['id']}] input={case['input']!r}: "
            f"expected legacy_output={case['legacy_output']!r}, got {got!r}"
        )


def test_cfr01b_category_coverage(corpus):
    categories = {c["category"] for c in corpus["fallback_cases"]}
    required = {
        "add_item",
        "remove_item",
        "change_quantity",
        "confirm_order",
        "cancel_order",
        "unknown",
        "query",
        "mixed",
        "social",
        "empty",
        "noise",
        "precedence",
        "historical_anomaly",
    }
    missing = required - categories
    assert not missing, f"corpus missing categories: {sorted(missing)}"


# =============================================
# CFR-02 — classifier path (known labels)
# =============================================

@pytest.mark.parametrize(
    "label,expected",
    [
        ("LABEL_0", "ADD_ITEM"),
        ("LABEL_1", "REMOVE_ITEM"),
        ("LABEL_2", "CHANGE_QUANTITY"),
        ("LABEL_3", "CONFIRM_ORDER"),
        ("LABEL_4", "CANCEL_ORDER"),
        ("LABEL_5", "UNKNOWN"),
    ],
)
def test_cfr02_classifier_known_labels(label, expected):
    adapter = _make_adapter_without_init()
    _install_legacy_state(adapter, classifier=_fake_classifier(label))
    assert adapter._classify_intent("qualquer mensagem") == expected


def test_cfr02b_classifier_corpus(corpus):
    for case in corpus["classifier_cases"]:
        adapter = _make_adapter_without_init()
        _install_legacy_state(
            adapter, classifier=_fake_classifier(case["label"])
        )
        got = adapter._classify_intent("qualquer mensagem")
        assert got == case["legacy_output"], (
            f"[{case['id']}] label={case['label']!r}: "
            f"expected {case['legacy_output']!r}, got {got!r}"
        )


# =============================================
# CFR-03 — unexpected classifier label (historical information loss)
# =============================================

def test_cfr03_unexpected_label_collapses_to_unknown():
    """
    Documents the historical information loss that T10-P31 / T10-P34
    / T10-P35 will correct in the new CommandRecognizer.

    In the legacy path, a classifier output outside intent_label_map
    collapses to the string "UNKNOWN". The new recognizer contract
    requires this case to raise at the first boundary capable of
    detecting the violation.
    """
    adapter = _make_adapter_without_init()
    _install_legacy_state(adapter, classifier=_fake_classifier("LABEL_99"))
    assert adapter._classify_intent("qualquer") == "UNKNOWN"


# =============================================
# CFR-04 — classifier failure falls back to deterministic
# =============================================

def test_cfr04_classifier_exception_falls_back_to_deterministic():
    adapter = _make_adapter_without_init()
    _install_legacy_state(adapter, classifier=_raising_classifier)
    # Fallback path: "quero brie" matches rule 4 -> ADD_ITEM.
    assert adapter._classify_intent("quero brie") == "ADD_ITEM"
    # Fallback path: unknown input -> UNKNOWN.
    assert adapter._classify_intent("olá") == "UNKNOWN"


def test_cfr04b_classifier_absent_uses_fallback():
    adapter = _make_adapter_without_init()
    _install_legacy_state(adapter, classifier=None)
    assert adapter._classify_intent("manda dois brie") == "ADD_ITEM"
    assert adapter._classify_intent("asdkjfh") == "UNKNOWN"


# =============================================
# CFR-05 — historical absence of REPLACE_ITEM
# =============================================

def test_cfr05_no_replace_item_emitted_in_corpus(corpus):
    outputs = {c["legacy_output"] for c in corpus["fallback_cases"]}
    assert "REPLACE_ITEM" not in outputs


def test_cfr05b_corpus_outputs_within_legacy_domain(corpus):
    legacy_domain = {
        "ADD_ITEM",
        "REMOVE_ITEM",
        "CHANGE_QUANTITY",
        "CONFIRM_ORDER",
        "CANCEL_ORDER",
        "UNKNOWN",
    }
    for case in corpus["fallback_cases"]:
        assert case["legacy_output"] in legacy_domain, (
            f"[{case['id']}] output {case['legacy_output']!r} outside "
            f"legacy domain"
        )


def test_cfr05c_troca_maps_to_change_quantity_historically():
    """
    Historical anomaly documented by T10-P36: the legacy recognizer
    maps 'troca ...' to CHANGE_QUANTITY, not to REPLACE_ITEM.
    """
    adapter = _make_adapter_without_init()
    _install_legacy_state(adapter, classifier=None)
    assert (
        adapter._classify_intent("troca o brie pelo provolone")
        == "CHANGE_QUANTITY"
    )


def test_cfr05d_substitui_maps_to_unknown_historically():
    """
    Historical absence of REPLACE_ITEM recognition documented by
    T10-P36: 'substitui ...' does not match any legacy rule.
    """
    adapter = _make_adapter_without_init()
    _install_legacy_state(adapter, classifier=None)
    assert adapter._classify_intent("substitui o brie") == "UNKNOWN"


# =============================================
# CFR-06 — precedence gotchas
# =============================================

@pytest.mark.parametrize(
    "message,expected",
    [
        ("muda para 5, tira 2", "CHANGE_QUANTITY"),
        ("tira 2, cancela tudo", "REMOVE_ITEM"),
        ("cancela tudo, quero brie", "ADD_ITEM"),
        ("na verdade, quero mussarela", "ADD_ITEM"),
    ],
)
def test_cfr06_precedence_first_match_wins(message, expected):
    adapter = _make_adapter_without_init()
    _install_legacy_state(adapter, classifier=None)
    assert adapter._classify_intent(message) == expected