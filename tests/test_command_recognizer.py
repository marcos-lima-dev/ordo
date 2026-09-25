import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from pipeline.command_recognizer import (
    CommandLabel,
    CommandRecognizer,
    RecognitionOutcome,
    RecognitionResult,
    UnexpectedClassifierOutput,
)


_CORPUS_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "command_recognizer_v1_corpus.json"
)

_MODULE_PATH = (
    Path(__file__).parent.parent / "pipeline" / "command_recognizer.py"
)


_LEGACY_LABEL_MAP = {
    "LABEL_0": CommandLabel.ADD_ITEM,
    "LABEL_1": CommandLabel.REMOVE_ITEM,
    "LABEL_2": CommandLabel.CHANGE_QUANTITY,
    "LABEL_3": CommandLabel.CONFIRM_ORDER,
    "LABEL_4": CommandLabel.CANCEL_ORDER,
    "LABEL_5": None,
}


@pytest.fixture(scope="module")
def corpus():
    return json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))


def _fake_classifier(label):
    def callable_(message):
        return [{"label": label, "score": 1.0}]
    return callable_


def _raising_classifier(message):
    raise RuntimeError("classifier failure")


def _recognizer_with_classifier(label):
    return CommandRecognizer(
        classifier=_fake_classifier(label),
        label_map=_LEGACY_LABEL_MAP,
    )


def _non_docstring_string_constants(tree):
    """
    Return all string constants in `tree` that are NOT docstrings.
    Used to check code (not documentation prose) for forbidden tokens.
    """
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

    result = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstring_value_ids
        ):
            result.append(node.value)
    return result


def _imported_module_names(tree):
    """Return the set of module names imported by `tree`."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
    return names


def _imported_symbol_names(tree):
    """Return the set of symbol names imported by `tree`."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.name)
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
    return names


# =============================================
# CR-01 — domain and enum
# =============================================

def test_cr01_command_label_has_exactly_five_values():
    assert {c.name for c in CommandLabel} == {
        "ADD_ITEM",
        "REMOVE_ITEM",
        "CHANGE_QUANTITY",
        "CONFIRM_ORDER",
        "CANCEL_ORDER",
    }


def test_cr01b_no_replace_item_in_command_label():
    assert "REPLACE_ITEM" not in {c.name for c in CommandLabel}


def test_cr01c_no_query_labels_in_command_label():
    assert "QUERY_PRICE" not in {c.name for c in CommandLabel}
    assert "QUERY_AVAILABILITY" not in {c.name for c in CommandLabel}


def test_cr01d_recognition_outcome_has_exactly_two_values():
    assert {o.name for o in RecognitionOutcome} == {
        "RECOGNIZED",
        "UNRECOGNIZED",
    }


def test_cr01e_no_invalid_outcome():
    assert "INVALID" not in {o.name for o in RecognitionOutcome}


def test_cr01f_recognition_result_is_frozen():
    from dataclasses import FrozenInstanceError
    r = RecognitionResult(RecognitionOutcome.UNRECOGNIZED)
    with pytest.raises(FrozenInstanceError):
        r.outcome = RecognitionOutcome.RECOGNIZED


# =============================================
# CR-02 — fallback corpus equivalence
# =============================================

def test_cr02_fallback_corpus_equivalence(corpus):
    """Every legacy fallback case must be reproduced by the new
    recognizer in the valid domain (RECOGNIZED maps to the same label;
    legacy UNKNOWN maps to UNRECOGNIZED)."""
    rec = CommandRecognizer()
    for case in corpus["fallback_cases"]:
        result = rec.recognize(case["input"])
        legacy = case["legacy_output"]
        if legacy == "UNKNOWN":
            assert result.outcome is RecognitionOutcome.UNRECOGNIZED, (
                f"[{case['id']}] input={case['input']!r}: expected "
                f"UNRECOGNIZED, got {result}"
            )
        else:
            assert result.outcome is RecognitionOutcome.RECOGNIZED, (
                f"[{case['id']}] input={case['input']!r}: expected "
                f"RECOGNIZED {legacy!r}, got {result}"
            )
            assert result.label.name == legacy, (
                f"[{case['id']}] input={case['input']!r}: "
                f"expected {legacy!r}, got {result.label.name!r}"
            )


# =============================================
# CR-03 — first-match-wins precedence
# =============================================

@pytest.mark.parametrize(
    "message,expected",
    [
        ("muda para 5, tira 2", CommandLabel.CHANGE_QUANTITY),
        ("tira 2, cancela tudo", CommandLabel.REMOVE_ITEM),
        ("cancela tudo, quero brie", CommandLabel.ADD_ITEM),
        ("na verdade, quero mussarela", CommandLabel.ADD_ITEM),
        ("coloca 3 kg, quero mais", CommandLabel.ADD_ITEM),
    ],
)
def test_cr03_first_match_wins(message, expected):
    rec = CommandRecognizer()
    result = rec.recognize(message)
    assert result.outcome is RecognitionOutcome.RECOGNIZED
    assert result.label is expected


# =============================================
# CR-04 — historical anomalies preserved
# =============================================

def test_cr04_troca_maps_to_change_quantity_historically():
    rec = CommandRecognizer()
    result = rec.recognize("troca o brie pelo provolone")
    assert result.outcome is RecognitionOutcome.RECOGNIZED
    assert result.label is CommandLabel.CHANGE_QUANTITY


def test_cr04b_substitui_maps_to_unrecognized_historically():
    rec = CommandRecognizer()
    result = rec.recognize("substitui o brie")
    assert result.outcome is RecognitionOutcome.UNRECOGNIZED


# =============================================
# CR-05 — QUERY, mixed, social, empty, noise
# =============================================

@pytest.mark.parametrize(
    "message",
    [
        "tem brie?",
        "quanto custa o brie?",
        "qual o preço e tem disponível?",
        "olá",
        "bom dia",
        "",
        "   ",
        "asdkjfh",
    ],
)
def test_cr05_non_command_inputs_unrecognized(message):
    rec = CommandRecognizer()
    result = rec.recognize(message)
    assert result.outcome is RecognitionOutcome.UNRECOGNIZED


def test_cr05b_mixed_message_add_item_historically():
    rec = CommandRecognizer()
    result = rec.recognize("tem brie, manda dois")
    assert result.outcome is RecognitionOutcome.RECOGNIZED
    assert result.label is CommandLabel.ADD_ITEM


# =============================================
# CR-06 — classifier known labels
# =============================================

@pytest.mark.parametrize(
    "label,expected",
    [
        ("LABEL_0", CommandLabel.ADD_ITEM),
        ("LABEL_1", CommandLabel.REMOVE_ITEM),
        ("LABEL_2", CommandLabel.CHANGE_QUANTITY),
        ("LABEL_3", CommandLabel.CONFIRM_ORDER),
        ("LABEL_4", CommandLabel.CANCEL_ORDER),
    ],
)
def test_cr06_classifier_known_labels(label, expected):
    rec = _recognizer_with_classifier(label)
    result = rec.recognize("qualquer mensagem")
    assert result.outcome is RecognitionOutcome.RECOGNIZED
    assert result.label is expected


# =============================================
# CR-07 — classifier historical UNKNOWN (LABEL_5)
# =============================================

def test_cr07_classifier_label_5_maps_to_unrecognized():
    rec = _recognizer_with_classifier("LABEL_5")
    result = rec.recognize("qualquer mensagem")
    assert result.outcome is RecognitionOutcome.UNRECOGNIZED
    assert result.label is None


# =============================================
# CR-08 — unexpected classifier label -> exception
# =============================================

def test_cr08_unexpected_classifier_label_raises():
    """
    Deliberate divergence from legacy (T10-P36):
    legacy: unexpected label -> "UNKNOWN"
    new:    unexpected label -> exception.
    """
    rec = _recognizer_with_classifier("LABEL_99")
    with pytest.raises(UnexpectedClassifierOutput) as excinfo:
        rec.recognize("qualquer mensagem")
    assert excinfo.value.raw_label == "LABEL_99"


def test_cr08b_unexpected_label_not_returned_as_unknown():
    rec = _recognizer_with_classifier("LABEL_99")
    try:
        result = rec.recognize("x")
    except UnexpectedClassifierOutput:
        return
    pytest.fail(
        f"recognizer returned {result!r} instead of raising"
    )


# =============================================
# CR-09 — classifier failure behavior (legacy preservation)
# =============================================

def test_cr09_classifier_exception_falls_back():
    rec = CommandRecognizer(
        classifier=_raising_classifier,
        label_map=_LEGACY_LABEL_MAP,
    )
    # Fallback path: "quero brie" matches rule 4 -> ADD_ITEM.
    result = rec.recognize("quero brie")
    assert result.outcome is RecognitionOutcome.RECOGNIZED
    assert result.label is CommandLabel.ADD_ITEM
    # Fallback path: unknown input -> UNRECOGNIZED.
    result = rec.recognize("olá")
    assert result.outcome is RecognitionOutcome.UNRECOGNIZED


def test_cr09b_classifier_absent_uses_fallback():
    rec = CommandRecognizer()
    result = rec.recognize("manda dois brie")
    assert result.outcome is RecognitionOutcome.RECOGNIZED
    assert result.label is CommandLabel.ADD_ITEM
    result = rec.recognize("asdkjfh")
    assert result.outcome is RecognitionOutcome.UNRECOGNIZED


def test_cr09c_classifier_requires_label_map():
    with pytest.raises(ValueError):
        CommandRecognizer(classifier=_fake_classifier("LABEL_0"))


# =============================================
# CR-10 — determinism
# =============================================

def test_cr10_determinism_fallback():
    rec = CommandRecognizer()
    msg = "quero brie"
    results = [rec.recognize(msg) for _ in range(5)]
    assert all(r == results[0] for r in results)


def test_cr10b_determinism_classifier():
    rec = _recognizer_with_classifier("LABEL_2")
    results = [rec.recognize("x") for _ in range(5)]
    assert all(r == results[0] for r in results)


# =============================================
# CR-11 — no REPLACE_ITEM in code (docstrings excluded)
# =============================================

def test_cr11_no_replace_item_in_module_code():
    """
    Non-docstring code must not reference REPLACE_ITEM.
    Docstrings may reference it to document its intentional absence.
    """
    source = _MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for value in _non_docstring_string_constants(tree):
        assert "REPLACE_ITEM" not in value, (
            f"non-docstring string references REPLACE_ITEM: {value!r}"
        )


# =============================================
# CR-12 — dependency isolation
# =============================================

def test_cr12_no_forbidden_imports():
    source = _MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    forbidden_modules = (
        "gliner",
        "transformers",
        "torch",
        "sklearn",
        "numpy",
        "benchmark",
        "order.state",
        "order.engine",
        "order.resolution_result",
        "order.query_resolution_result",
        "order.operation_resolver",
        "order.catalog_retriever",
        "order.product_resolver",
        "pipeline.semantic_intent_router",
        "pipeline.query_resolution_pipeline",
        "pipeline.resolution_pipeline",
        "pipeline.query_intent_provider",
        "pipeline.query_intent_bootstrap",
        "pipeline.command_evidence_provider",
    )
    imported = _imported_module_names(tree)
    for token in forbidden_modules:
        for name in imported:
            assert token not in name, (
                f"command_recognizer.py imports forbidden module "
                f"matching {token!r}: {name!r}"
            )


def test_cr12b_no_command_evidence_symbol_in_code():
    """
    Recognizer must not import the evidence provider (T10-P32).
    Docstrings may reference it to document the boundary.
    """
    source = _MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    for value in _non_docstring_string_constants(tree):
        assert "CommandEvidence" not in value, (
            f"non-docstring string references CommandEvidence: {value!r}"
        )

    imported_modules = _imported_module_names(tree)
    assert not any(
        "command_evidence_provider" in name for name in imported_modules
    )

    imported_symbols = _imported_symbol_names(tree)
    assert "CommandEvidence" not in imported_symbols


def test_cr12c_no_semantic_intent_or_operation_type():
    """
    Non-docstring code must not reference SemanticIntent or
    OperationType. Docstrings may reference them to document the
    boundary.
    """
    source = _MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    for value in _non_docstring_string_constants(tree):
        for token in ("SemanticIntent", "OperationType"):
            assert token not in value, (
                f"non-docstring string references {token}: {value!r}"
            )

    imported_modules = _imported_module_names(tree)
    for token in ("semantic_intent_router", "resolved_operation"):
        for name in imported_modules:
            assert token not in name, (
                f"command_recognizer.py imports forbidden module "
                f"matching {token!r}: {name!r}"
            )

    imported_symbols = _imported_symbol_names(tree)
    for token in ("SemanticIntent", "OperationType"):
        assert token not in imported_symbols, (
            f"command_recognizer.py imports forbidden symbol {token!r}"
        )