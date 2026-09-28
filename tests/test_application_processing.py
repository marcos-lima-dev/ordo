import ast
import sys
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from order.engine import OrderEngine
from order.resolution_result import OutcomeType, ResolutionResult
from order.state import OrderState

from pipeline.application_orchestrator import (
    OrchestrationOutcome,
    orchestrate_command,
)
from pipeline.application_processing import (
    ApplicationProcessor,
    ProcessingResult,
)
from pipeline.channel_identity import ChannelIdentity
from pipeline.command_evidence_provider import CommandEvidenceProvider
from pipeline.command_recognizer import (
    CommandRecognizer,
    RecognitionOutcome,
    RecognitionResult,
    UnexpectedClassifierOutput,
)
from pipeline.conversation_mapping import InMemoryConversationMappingStore
from pipeline.conversation_session import InMemoryConversationSessionStore
from pipeline.dispatch_plan import (
    DispatchAction,
    DispatchTarget,
)
from pipeline.idempotency import (
    ExternalMessageId,
    InMemoryIdempotencyStore,
)
from pipeline.query_intent_provider import (
    QueryIntentProvider,
    QueryIntentSignal,
)
from pipeline.recognizer_command_evidence_provider import (
    RecognizerCommandEvidenceProvider,
)
from pipeline.signal_observation import (
    CommandEvidence,
    CommandObservation,
    QueryObservation,
    SignalObservation,
)


_MODULE_PATH = (
    Path(__file__).parent.parent / "pipeline" / "application_processing.py"
)


# =============================================
# Stubs and fakes
# =============================================

class _StubQueryProvider(QueryIntentProvider):
    def __init__(self, signal=QueryIntentSignal.UNRESOLVED):
        self._signal = signal
        self.calls = []

    def predict(self, message):
        self.calls.append(message)
        return self._signal


class _RaisingQueryProvider(QueryIntentProvider):
    def __init__(self, exc):
        self._exc = exc

    def predict(self, message):
        raise self._exc


class _StubCommandProvider(CommandEvidenceProvider):
    def __init__(self, evidence=CommandEvidence.INDETERMINATE):
        self._evidence = evidence
        self.calls = []

    def predict(self, message):
        self.calls.append(message)
        return self._evidence


class _RaisingCommandProvider(CommandEvidenceProvider):
    def __init__(self, exc):
        self._exc = exc

    def predict(self, message):
        raise self._exc


class _StubRecognizer(CommandRecognizer):
    """Recognizer stub used to build a real RecognizerCommandEvidenceProvider."""

    def __init__(self, outcome, label=None):
        self._outcome = outcome
        self._label = label

    def recognize(self, message):
        return RecognitionResult(outcome=self._outcome, label=self._label)


# =============================================
# AP-01 / AP-02 — provider call counts
# =============================================

def test_ap01_query_provider_called_exactly_once():
    q = _StubQueryProvider(QueryIntentSignal.QUERY_PRICE)
    c = _StubCommandProvider(CommandEvidence.PRESENT)
    processor = ApplicationProcessor(q, c)
    processor.process("manda provolone")
    assert q.calls == ["manda provolone"]


def test_ap02_command_provider_called_exactly_once():
    q = _StubQueryProvider()
    c = _StubCommandProvider(CommandEvidence.PRESENT)
    processor = ApplicationProcessor(q, c)
    processor.process("manda provolone")
    assert c.calls == ["manda provolone"]


# =============================================
# AP-03 / AP-04 / AP-05 — SignalObservation and plan
# =============================================

def test_ap03_independent_signals_preserved():
    q = _StubQueryProvider(QueryIntentSignal.QUERY_PRICE)
    c = _StubCommandProvider(CommandEvidence.PRESENT)
    processor = ApplicationProcessor(q, c)
    result = processor.process("quanto custa o brie e manda dois")
    assert result.observation.query is not None
    assert result.observation.command is not None
    assert result.observation.query.signal is QueryIntentSignal.QUERY_PRICE
    assert result.observation.command.evidence is CommandEvidence.PRESENT


def test_ap04_plan_receives_the_produced_observation():
    q = _StubQueryProvider(QueryIntentSignal.QUERY_AVAILABILITY)
    c = _StubCommandProvider(CommandEvidence.INDETERMINATE)
    processor = ApplicationProcessor(q, c)
    result = processor.process("tem brie?")

    # Planner called on the exact same observation produced.
    by_target = {d.target: d.action for d in result.dispatch_plan.decisions}
    assert by_target[DispatchTarget.QUERY] is DispatchAction.DISPATCH
    assert (
        by_target[DispatchTarget.COMMAND]
        is DispatchAction.NO_DISPATCH_INDETERMINATE
    )


def test_ap05_processing_result_shape():
    assert {f.name for f in fields(ProcessingResult)} == {
        "observation", "dispatch_plan",
    }


def test_ap05b_processing_result_is_frozen():
    q = _StubQueryProvider()
    c = _StubCommandProvider()
    result = ApplicationProcessor(q, c).process("x")
    with pytest.raises(FrozenInstanceError):
        result.observation = None


# =============================================
# AP-06 — QUERY case, no read-side executed
# =============================================

def test_ap06_query_case_no_read_side():
    q = _StubQueryProvider(QueryIntentSignal.QUERY_PRICE)
    c = _StubCommandProvider(CommandEvidence.INDETERMINATE)
    result = ApplicationProcessor(q, c).process("quanto custa o brie?")
    by_target = {d.target: d.action for d in result.dispatch_plan.decisions}
    assert by_target[DispatchTarget.QUERY] is DispatchAction.DISPATCH
    # No FactRetrievalResult anywhere. Only observation + plan.
    assert not hasattr(result, "fact_retrieval")
    assert not hasattr(result, "query_resolution")


# =============================================
# AP-07 — COMMAND case, no execution
# =============================================

def test_ap07_command_case_no_execution():
    q = _StubQueryProvider(QueryIntentSignal.UNRESOLVED)
    c = _StubCommandProvider(CommandEvidence.PRESENT)
    result = ApplicationProcessor(q, c).process("manda provolone")
    by_target = {d.target: d.action for d in result.dispatch_plan.decisions}
    assert by_target[DispatchTarget.COMMAND] is DispatchAction.DISPATCH
    assert not hasattr(result, "execution_result")
    assert not hasattr(result, "caller_result")


# =============================================
# AP-08 — UNRESOLVED / INDETERMINATE preserved
# =============================================

def test_ap08_unresolved_and_indeterminate_preserved():
    q = _StubQueryProvider(QueryIntentSignal.UNRESOLVED)
    c = _StubCommandProvider(CommandEvidence.INDETERMINATE)
    result = ApplicationProcessor(q, c).process("olá")
    assert result.observation.query.signal is QueryIntentSignal.UNRESOLVED
    assert (
        result.observation.command.evidence
        is CommandEvidence.INDETERMINATE
    )
    by_target = {d.target: d.action for d in result.dispatch_plan.decisions}
    assert (
        by_target[DispatchTarget.QUERY]
        is DispatchAction.NO_DISPATCH_UNRESOLVED
    )
    assert (
        by_target[DispatchTarget.COMMAND]
        is DispatchAction.NO_DISPATCH_INDETERMINATE
    )


# =============================================
# AP-09 / AP-10 — provider failure and invalid output propagate
# =============================================

def test_ap09_query_provider_failure_propagates():
    q = _RaisingQueryProvider(RuntimeError("query boom"))
    c = _StubCommandProvider()
    with pytest.raises(RuntimeError, match="query boom"):
        ApplicationProcessor(q, c).process("x")


def test_ap09b_command_provider_failure_propagates():
    q = _StubQueryProvider()
    c = _RaisingCommandProvider(RuntimeError("command boom"))
    with pytest.raises(RuntimeError, match="command boom"):
        ApplicationProcessor(q, c).process("x")


def test_ap10_invalid_recognizer_output_propagates():
    """RecognizerCommandEvidenceProvider surfaces UnexpectedClassifierOutput."""
    # Build a stub recognizer that emits UnexpectedClassifierOutput.
    class _RaisingRecognizer(CommandRecognizer):
        def recognize(self, message):
            raise UnexpectedClassifierOutput("LABEL_99")

    provider = RecognizerCommandEvidenceProvider(
        recognizer=_RaisingRecognizer()
    )
    q = _StubQueryProvider()
    with pytest.raises(UnexpectedClassifierOutput):
        ApplicationProcessor(q, provider).process("x")


# =============================================
# AP-11 / AP-12 — dependency isolation (AST)
# =============================================

_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "pipeline.command_evidence_provider",
    "pipeline.dispatch_plan",
    "pipeline.dispatch_planner",
    "pipeline.query_intent_provider",
    "pipeline.signal_observation",
}


def _non_docstring_strings(tree):
    docstring_ids = set()
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
                docstring_ids.add(id(node.body[0].value))
    return [
        n.value for n in ast.walk(tree)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, str)
        and id(n) not in docstring_ids
    ]


def test_ap11_module_imports_only_allowed():
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module in _ALLOWED_IMPORTS, (
                f"unexpected import: {node.module}"
            )
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name in _ALLOWED_IMPORTS, (
                    f"unexpected import: {alias.name}"
                )


def test_ap11b_no_state_or_engine_symbols_in_code():
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    forbidden = (
        "OrderState",
        "OrderEngine",
        "application_orchestrator",
        "command_execution",
        "idempotency",
        "query_read_side",
        "compose_query_read_side",
        "retrieve_fact",
        "ChannelIdentity",
        "ConversationId",
        "ExternalMessageId",
        "channel_identity",
        "conversation_mapping",
        "conversation_session",
        "orchestrate_command",
        "application_caller",
    )
    for value in _non_docstring_strings(tree):
        for token in forbidden:
            assert token not in value, (
                f"non-docstring string references {token!r}: {value!r}"
            )


def test_ap11c_no_forbidden_imports_by_module_or_symbol():
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for tok in (
                "order", "idempotency", "channel", "conversation",
                "application_orchestrator", "command_execution",
                "application_caller", "query_read_side",
            ):
                assert tok not in node.module, (
                    f"imports forbidden module {node.module!r}"
                )
            for alias in node.names:
                for tok in ("OrderState", "OrderEngine"):
                    assert alias.name != tok


def test_ap12_no_channel_identity_imported():
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert "channel_identity" not in node.module
            assert "conversation_mapping" not in node.module


# =============================================
# AP-13 — Shadow structural proof
# =============================================

def test_ap13_shadow_produces_only_observation_and_plan():
    q = _StubQueryProvider(QueryIntentSignal.UNRESOLVED)
    c = _StubCommandProvider(CommandEvidence.PRESENT)
    result = ApplicationProcessor(q, c).process("manda o provolone")
    assert isinstance(result.observation, SignalObservation)
    # No claim, no state, no engine touched. Structural proof: type surface.
    assert {f.name for f in fields(result)} == {"observation", "dispatch_plan"}


# =============================================
# Integration — synthetic Shadow flow
# =============================================

def test_integration_synthetic_shadow_telegram():
    """
    ChannelIdentity -> ConversationId -> processor.process -> STOP.
    No orchestrator, no engine, no state mutation.
    """
    mapping = InMemoryConversationMappingStore()
    ci = ChannelIdentity(channel="telegram", external_conversation_id="12345")
    cid = mapping.get_or_create(ci)
    assert cid is not None

    q = _StubQueryProvider(QueryIntentSignal.UNRESOLVED)
    c = _StubCommandProvider(CommandEvidence.PRESENT)
    processor = ApplicationProcessor(q, c)

    text = "manda o provolone"
    emid = ExternalMessageId(value="42")
    assert emid.value == "42"

    result = processor.process(text)
    assert result.observation.command.evidence is CommandEvidence.PRESENT
    by_target = {d.target: d.action for d in result.dispatch_plan.decisions}
    assert by_target[DispatchTarget.COMMAND] is DispatchAction.DISPATCH


def test_integration_synthetic_shadow_web():
    mapping = InMemoryConversationMappingStore()
    ci = ChannelIdentity(channel="web", external_conversation_id="abc")
    cid = mapping.get_or_create(ci)
    assert cid is not None

    q = _StubQueryProvider(QueryIntentSignal.QUERY_PRICE)
    c = _StubCommandProvider(CommandEvidence.INDETERMINATE)
    processor = ApplicationProcessor(q, c)
    result = processor.process("quanto custa o brie?")

    by_target = {d.target: d.action for d in result.dispatch_plan.decisions}
    assert by_target[DispatchTarget.QUERY] is DispatchAction.DISPATCH
    assert (
        by_target[DispatchTarget.COMMAND]
        is DispatchAction.NO_DISPATCH_INDETERMINATE
    )


# =============================================
# Execution compatibility — plan/observation consumed by orchestrator
# =============================================

def test_execution_compatibility_processor_output_feeds_orchestrator():
    """
    Prove that ProcessingResult's observation + dispatch_plan can be
    fed to orchestrate_command as-is. Processor is NOT the executor.
    """
    sessions = InMemoryConversationSessionStore()
    idem = InMemoryIdempotencyStore()
    engine = OrderEngine()
    mapping = InMemoryConversationMappingStore()

    q = _StubQueryProvider(QueryIntentSignal.UNRESOLVED)
    c = _StubCommandProvider(CommandEvidence.PRESENT)
    processor = ApplicationProcessor(q, c)

    ci = ChannelIdentity(channel="telegram", external_conversation_id="12345")
    cid = mapping.get_or_create(ci)

    result = processor.process("manda o provolone")

    def _resolver(message, state):
        return ResolutionResult(
            outcome=OutcomeType.OPERATION,
            operation={
                "type": "ADD_ITEM",
                "product_id": "CQ-46",
                "product_term": "provolone",
                "quantity_value": 1.0,
                "quantity_unit": None,
                "target_item_id": None,
                "replacement_product_id": None,
            },
            evidence=[],
        )

    orchestration = orchestrate_command(
        cid,
        ExternalMessageId(value="42"),
        "manda o provolone",
        result.observation,
        result.dispatch_plan,
        engine,
        sessions,
        idem,
        resolve_operation_fn=_resolver,
    )
    assert orchestration.outcome is OrchestrationOutcome.PROCESSED
    assert len(sessions.get_or_create(cid).items) == 1