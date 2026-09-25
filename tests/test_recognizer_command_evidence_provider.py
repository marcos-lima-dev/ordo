import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from pipeline.command_evidence_provider import CommandEvidenceProvider
from pipeline.command_recognizer import (
    CommandLabel,
    RecognitionOutcome,
    RecognitionResult,
    UnexpectedClassifierOutput,
)
from pipeline.recognizer_command_evidence_provider import (
    RecognizerCommandEvidenceProvider,
)
from pipeline.signal_observation import CommandEvidence


_MODULE_PATH = (
    Path(__file__).parent.parent
    / "pipeline"
    / "recognizer_command_evidence_provider.py"
)


# =============================================
# Test doubles
# =============================================

class _StubRecognizer:
    """Recognizer stub returning a fixed RecognitionResult."""

    def __init__(self, outcome, label=None):
        self._outcome = outcome
        self._label = label
        self.calls = []

    def recognize(self, message):
        self.calls.append(message)
        return RecognitionResult(outcome=self._outcome, label=self._label)


class _RaisingRecognizer:
    """Recognizer stub raising a fixed exception."""

    def __init__(self, exc):
        self._exc = exc
        self.calls = []

    def recognize(self, message):
        self.calls.append(message)
        raise self._exc


# =============================================
# CE-01 — subclass of CommandEvidenceProvider
# =============================================

def test_ce01_provider_is_subclass():
    assert issubclass(
        RecognizerCommandEvidenceProvider, CommandEvidenceProvider
    )


def test_ce01b_instance_is_command_evidence_provider():
    stub = _StubRecognizer(RecognitionOutcome.UNRECOGNIZED)
    p = RecognizerCommandEvidenceProvider(recognizer=stub)
    assert isinstance(p, CommandEvidenceProvider)


# =============================================
# CE-02 — recognizer is mandatory
# =============================================

def test_ce02_recognizer_is_required():
    with pytest.raises(TypeError):
        RecognizerCommandEvidenceProvider()


# =============================================
# CE-03 / CE-04 — frozen mapping
# =============================================

def test_ce03_recognized_maps_to_present():
    stub = _StubRecognizer(
        RecognitionOutcome.RECOGNIZED, CommandLabel.ADD_ITEM
    )
    p = RecognizerCommandEvidenceProvider(recognizer=stub)
    assert p.predict("qualquer") is CommandEvidence.PRESENT


def test_ce04_unrecognized_maps_to_indeterminate():
    stub = _StubRecognizer(RecognitionOutcome.UNRECOGNIZED)
    p = RecognizerCommandEvidenceProvider(recognizer=stub)
    assert p.predict("qualquer") is CommandEvidence.INDETERMINATE


# =============================================
# CE-05 / CE-06 — exception propagation
# =============================================

def test_ce05_unexpected_classifier_output_propagates():
    exc = UnexpectedClassifierOutput("LABEL_99")
    stub = _RaisingRecognizer(exc)
    p = RecognizerCommandEvidenceProvider(recognizer=stub)
    with pytest.raises(UnexpectedClassifierOutput) as excinfo:
        p.predict("qualquer")
    assert excinfo.value.raw_label == "LABEL_99"


def test_ce06_other_exception_propagates():
    stub = _RaisingRecognizer(RuntimeError("internal"))
    p = RecognizerCommandEvidenceProvider(recognizer=stub)
    with pytest.raises(RuntimeError, match="internal"):
        p.predict("qualquer")


def test_ce06b_exception_not_converted_to_evidence():
    """No exception may collapse into a CommandEvidence value."""
    stub = _RaisingRecognizer(RuntimeError("boom"))
    p = RecognizerCommandEvidenceProvider(recognizer=stub)
    try:
        result = p.predict("x")
    except RuntimeError:
        return
    assert result not in CommandEvidence, (
        "provider returned an evidence value during operational failure"
    )


# =============================================
# CE-07 — ABSENT is not producible by v1
# =============================================

@pytest.mark.parametrize(
    "outcome,label,expected",
    [
        (
            RecognitionOutcome.RECOGNIZED,
            CommandLabel.ADD_ITEM,
            CommandEvidence.PRESENT,
        ),
        (
            RecognitionOutcome.RECOGNIZED,
            CommandLabel.REMOVE_ITEM,
            CommandEvidence.PRESENT,
        ),
        (
            RecognitionOutcome.RECOGNIZED,
            CommandLabel.CHANGE_QUANTITY,
            CommandEvidence.PRESENT,
        ),
        (
            RecognitionOutcome.RECOGNIZED,
            CommandLabel.CONFIRM_ORDER,
            CommandEvidence.PRESENT,
        ),
        (
            RecognitionOutcome.RECOGNIZED,
            CommandLabel.CANCEL_ORDER,
            CommandEvidence.PRESENT,
        ),
        (
            RecognitionOutcome.UNRECOGNIZED,
            None,
            CommandEvidence.INDETERMINATE,
        ),
    ],
)
def test_ce07_no_valid_path_produces_absent(outcome, label, expected):
    stub = _StubRecognizer(outcome, label)
    p = RecognizerCommandEvidenceProvider(recognizer=stub)
    result = p.predict("qualquer")
    assert result is not CommandEvidence.ABSENT
    assert result is expected


def test_ce07b_absent_not_returned_across_many_inputs():
    """Behavioral sweep: no input yields ABSENT."""
    for outcome in RecognitionOutcome:
        stub = _StubRecognizer(outcome)
        p = RecognizerCommandEvidenceProvider(recognizer=stub)
        for msg in ("", "olá", "tem brie?", "quero brie", "asdkjfh"):
            result = p.predict(msg)
            assert result is not CommandEvidence.ABSENT


# =============================================
# CE-08 — substitutability
# =============================================

def test_ce08_substitutability():
    stub_a = _StubRecognizer(
        RecognitionOutcome.RECOGNIZED, CommandLabel.ADD_ITEM
    )
    stub_b = _StubRecognizer(RecognitionOutcome.UNRECOGNIZED)
    providers = [
        RecognizerCommandEvidenceProvider(recognizer=stub_a),
        RecognizerCommandEvidenceProvider(recognizer=stub_b),
    ]
    for p in providers:
        assert isinstance(p, CommandEvidenceProvider)
    assert [p.predict("x") for p in providers] == [
        CommandEvidence.PRESENT,
        CommandEvidence.INDETERMINATE,
    ]


# =============================================
# CE-09 — no dependence on CommandLabel
# =============================================

def test_ce09_no_command_label_import():
    """Provider must not import CommandLabel."""
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                assert alias.name != "CommandLabel", (
                    "provider must not import CommandLabel"
                )
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "CommandLabel"


def test_ce09b_no_attribute_access_to_label():
    """Provider must not access any `.label` attribute in code."""
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr != "label", (
                f"provider accesses .label at line {node.lineno}"
            )


def test_ce09c_decision_ignores_label_value():
    """Behavioral: label value must not affect the outcome mapping."""
    outcomes = [
        (RecognitionOutcome.RECOGNIZED, CommandLabel.ADD_ITEM),
        (RecognitionOutcome.RECOGNIZED, CommandLabel.CANCEL_ORDER),
        (RecognitionOutcome.UNRECOGNIZED, None),
    ]
    for outcome, label in outcomes:
        stub = _StubRecognizer(outcome, label)
        p = RecognizerCommandEvidenceProvider(recognizer=stub)
        result = p.predict("x")
        if outcome is RecognitionOutcome.RECOGNIZED:
            assert result is CommandEvidence.PRESENT
        else:
            assert result is CommandEvidence.INDETERMINATE


# =============================================
# CE-10 — no dispatch / resolution / execution authority
# =============================================

def test_ce10_no_forbidden_methods():
    forbidden = (
        "dispatch", "route", "plan", "authorize",
        "execute", "apply", "resolve",
    )
    for name in forbidden:
        assert not hasattr(
            RecognizerCommandEvidenceProvider, name
        ), f"provider must not expose {name!r}"


def test_ce10b_minimal_public_surface():
    """The only public method exposed by the provider is `predict`."""
    public = [
        n for n in dir(RecognizerCommandEvidenceProvider)
        if not n.startswith("_")
    ]
    assert set(public) == {"predict"}


# =============================================
# CE-11 — dependency isolation
# =============================================

def test_ce11_no_forbidden_imports():
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    forbidden_modules = (
        "gliner", "transformers", "torch", "sklearn", "numpy",
        "benchmark",
        "order.state", "order.engine",
        "order.resolution_result", "order.query_resolution_result",
        "order.operation_resolver", "order.catalog_retriever",
        "order.product_resolver",
        "pipeline.semantic_intent_router",
        "pipeline.query_resolution_pipeline",
        "pipeline.resolution_pipeline",
        "pipeline.query_intent_provider",
        "pipeline.query_intent_bootstrap",
        "pipeline.modular",
        "pipeline.conversation_processor",
        "pipeline.hybrid_v1",
        "pipeline.hybrid_v2",
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for token in forbidden_modules:
                assert token not in node.module, (
                    f"provider imports forbidden {token!r}"
                )
        if isinstance(node, ast.Import):
            for alias in node.names:
                for token in forbidden_modules:
                    assert token not in alias.name


def test_ce11b_only_allowed_modules_imported():
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    allowed_from = {
        "__future__",
        "pipeline.command_evidence_provider",
        "pipeline.command_recognizer",
        "pipeline.signal_observation",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module in allowed_from, (
                f"unexpected import: {node.module}"
            )


# =============================================
# CE-12 — determinism
# =============================================

def test_ce12_determinism_recognized():
    stub = _StubRecognizer(
        RecognitionOutcome.RECOGNIZED, CommandLabel.ADD_ITEM
    )
    p = RecognizerCommandEvidenceProvider(recognizer=stub)
    results = [p.predict("x") for _ in range(5)]
    assert all(r is CommandEvidence.PRESENT for r in results)


def test_ce12b_determinism_unrecognized():
    stub = _StubRecognizer(RecognitionOutcome.UNRECOGNIZED)
    p = RecognizerCommandEvidenceProvider(recognizer=stub)
    results = [p.predict("x") for _ in range(5)]
    assert all(r is CommandEvidence.INDETERMINATE for r in results)


# =============================================
# CE-13 — no exception capture
# =============================================

def test_ce13_no_try_in_module():
    """The provider must not capture exceptions from the recognizer."""
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    try_nodes = [n for n in ast.walk(tree) if isinstance(n, ast.Try)]
    assert not try_nodes, (
        f"provider must not contain try/except; found {len(try_nodes)}"
    )


def test_ce13b_no_except_handler_in_module():
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    handlers = [
        n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)
    ]
    assert not handlers, (
        f"provider must not contain except handlers; "
        f"found {len(handlers)}"
    )


# =============================================
# CE-14 — recognize called exactly once per predict
# =============================================

def test_ce14_recognize_called_exactly_once_per_predict():
    stub = _StubRecognizer(
        RecognitionOutcome.RECOGNIZED, CommandLabel.ADD_ITEM
    )
    p = RecognizerCommandEvidenceProvider(recognizer=stub)
    p.predict("a")
    p.predict("b")
    p.predict("c")
    assert stub.calls == ["a", "b", "c"]


def test_ce14b_recognize_called_even_for_unrecognized():
    stub = _StubRecognizer(RecognitionOutcome.UNRECOGNIZED)
    p = RecognizerCommandEvidenceProvider(recognizer=stub)
    p.predict("x")
    assert stub.calls == ["x"]


def test_ce14c_recognize_called_once_for_raising_recognizer():
    stub = _RaisingRecognizer(RuntimeError("boom"))
    p = RecognizerCommandEvidenceProvider(recognizer=stub)
    with pytest.raises(RuntimeError):
        p.predict("x")
    assert stub.calls == ["x"]