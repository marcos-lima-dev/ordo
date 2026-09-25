import ast
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from order.engine import OrderEngine
from order.query_resolution_result import (
    QueryResolutionResult,
    QueryResolutionStatus,
)
from order.resolution_result import OutcomeType, ResolutionResult
from order.resolved_query import QueryType
from order.state import OrderState

from pipeline.application_caller import invoke
from pipeline.command_execution import (
    CommandExecutionStatus,
    compose_command_execution,
)
from pipeline.command_safety_guard import (
    CommandSafetyGuard,
    GuardDecision,
    REASON_CODE_OVERFLOW,
    SafetyGuardFailure,
    SafetyResult,
    make_guarded_resolve_operation,
)
from pipeline.dispatch_plan import (
    DispatchAction,
    DispatchDecision,
    DispatchPlan,
    DispatchTarget,
)
from pipeline.query_intent_provider import QueryIntentSignal
from pipeline.signal_observation import (
    CommandEvidence,
    CommandObservation,
    QueryObservation,
    SignalObservation,
)


_MODULE_PATH = (
    Path(__file__).parent.parent / "pipeline" / "command_safety_guard.py"
)


# =============================================
# Empirical corpus (frozen from the diagnostic)
# =============================================

_FAKE_ENTITIES = {
    "manda 5kg de provolone e 2 gorgonzolas": [
        {"label": "produto", "text": "provolone", "start": 13, "end": 22, "score": 0.95},
        {"label": "produto", "text": "gorgonzolas", "start": 27, "end": 38, "score": 0.80},
    ],
    "manda provolone e gorgonzola": [
        {"label": "produto", "text": "provolone", "start": 6, "end": 15, "score": 0.82},
        {"label": "produto", "text": "gorgonzola", "start": 18, "end": 28, "score": 0.80},
    ],
    "5kg de provolone, 2kg de parmesão e 1kg de brie": [
        {"label": "produto", "text": "provolone", "start": 7, "end": 16, "score": 0.97},
        {"label": "produto", "text": "parmesão", "start": 25, "end": 33, "score": 0.94},
        {"label": "produto", "text": "brie", "start": 43, "end": 47, "score": 0.96},
    ],
    "manda 2 provolones e tira o gorgonzola": [
        {"label": "produto", "text": "provolones", "start": 8, "end": 18, "score": 0.92},
        {"label": "produto", "text": "gorgonzola", "start": 28, "end": 38, "score": 0.86},
    ],
    "manda provolone e brie": [
        {"label": "produto", "text": "provolone", "start": 6, "end": 15, "score": 0.73},
        {"label": "produto", "text": "brie", "start": 18, "end": 22, "score": 0.77},
    ],
    "manda provolone, brie e parmesão": [
        {"label": "produto", "text": "provolone", "start": 6, "end": 15, "score": 0.95},
        {"label": "produto", "text": "brie", "start": 17, "end": 21, "score": 0.95},
        {"label": "produto", "text": "parmesão", "start": 24, "end": 32, "score": 0.88},
    ],
    "manda 2 provolones e 3 bries": [
        {"label": "produto", "text": "provolones", "start": 8, "end": 18, "score": 0.97},
        {"label": "produto", "text": "bries", "start": 23, "end": 28, "score": 0.95},
    ],
    "adiciona provolone e remove gorgonzola": [
        {"label": "produto", "text": "provolone", "start": 9, "end": 18, "score": 0.94},
        {"label": "produto", "text": "gorgonzola", "start": 28, "end": 38, "score": 0.89},
    ],
    "tira brie e gorgonzola": [
        {"label": "produto", "text": "tira brie e gorgonzola", "start": 0, "end": 22, "score": 0.57},
    ],
    "manda mais provolone e também gorgonzola": [
        {"label": "produto", "text": "provolone", "start": 11, "end": 20, "score": 0.98},
        {"label": "produto", "text": "gorgonzola", "start": 30, "end": 40, "score": 0.92},
    ],
    "manda 5kg de provolone forma 5kg": [
        {"label": "produto", "text": "provolone", "start": 13, "end": 22, "score": 0.88},
    ],
    "quero 2 peças de 5kg de provolone": [
        {"label": "produto", "text": "provolone", "start": 24, "end": 33, "score": 0.83},
    ],
    "manda o provolone de 5kg": [
        {"label": "produto", "text": "provolone", "start": 8, "end": 17, "score": 0.89},
    ],
    "troca a quantidade do provolone de 2 para 5": [
        {"label": "produto", "text": "provolone", "start": 22, "end": 31, "score": 0.93},
    ],
    "tem provolone de 5kg?": [
        {"label": "produto", "text": "provolone", "start": 4, "end": 13, "score": 0.85},
    ],
    "quanto está 1kg de provolone?": [
        {"label": "produto", "text": "provolone", "start": 19, "end": 28, "score": 0.88},
    ],
    "manda 6 bisnagas de Catupiry": [
        {"label": "marca", "text": "Catupiry", "start": 20, "end": 28, "score": 0.47},
    ],
    "manda 10kg daquela manteiga sem sal": [
        {"label": "produto", "text": "manteiga", "start": 19, "end": 27, "score": 0.46},
    ],
    "quero 3 potes de requeijão": [
        {"label": "produto", "text": "requeijão", "start": 17, "end": 26, "score": 0.35},
    ],
    "manda 2 kg de mussarela": [
        {"label": "produto", "text": "mussarela", "start": 14, "end": 23, "score": 0.79},
    ],
    "manda o provolone": [
        {"label": "produto", "text": "provolone", "start": 8, "end": 17, "score": 0.76},
    ],
    "quero provolone": [
        {"label": "produto", "text": "provolone", "start": 6, "end": 15, "score": 0.77},
    ],
    "coloca 1 brie": [
        {"label": "produto", "text": "brie", "start": 9, "end": 13, "score": 0.65},
    ],
}

_POSITIVE = [
    "manda 5kg de provolone e 2 gorgonzolas",
    "manda provolone e gorgonzola",
    "5kg de provolone, 2kg de parmesão e 1kg de brie",
    "manda 2 provolones e tira o gorgonzola",
    "manda provolone e brie",
    "manda provolone, brie e parmesão",
    "manda 2 provolones e 3 bries",
    "adiciona provolone e remove gorgonzola",
    "tira brie e gorgonzola",
    "manda mais provolone e também gorgonzola",
]

_NEGATIVE = [
    "manda 5kg de provolone forma 5kg",
    "quero 2 peças de 5kg de provolone",
    "manda o provolone de 5kg",
    "troca a quantidade do provolone de 2 para 5",
    "tem provolone de 5kg?",
    "quanto está 1kg de provolone?",
    "manda 6 bisnagas de Catupiry",
    "manda 10kg daquela manteiga sem sal",
    "quero 3 potes de requeijão",
    "manda 2 kg de mussarela",
    "manda o provolone",
    "quero provolone",
    "coloca 1 brie",
]


def _fake_extractor(message, labels, *, threshold=0.3):
    return list(_FAKE_ENTITIES.get(message, []))


def _guard():
    return CommandSafetyGuard(_fake_extractor)


def _command_plan():
    return DispatchPlan(decisions=(
        DispatchDecision(
            DispatchTarget.QUERY, DispatchAction.NO_DISPATCH_NO_OBSERVATION
        ),
        DispatchDecision(
            DispatchTarget.COMMAND, DispatchAction.DISPATCH
        ),
    ))


def _command_observation():
    return SignalObservation(
        query=None,
        command=CommandObservation(evidence=CommandEvidence.PRESENT),
    )


# =============================================
# CSG-01 — enum / result shape
# =============================================

def test_csg01_decision_enum():
    assert {d.name for d in GuardDecision} == {
        "SAFE", "REPRESENTATIONAL_OVERFLOW",
    }


def test_csg01b_result_frozen():
    r = SafetyResult(decision=GuardDecision.SAFE)
    with pytest.raises(FrozenInstanceError):
        r.decision = GuardDecision.REPRESENTATIONAL_OVERFLOW


def test_csg01c_result_fields_exact():
    fields = set(SafetyResult.__dataclass_fields__.keys())
    assert fields == {"decision", "evidence"}


# =============================================
# CSG-02 — empirical corpus regression
# =============================================

@pytest.mark.parametrize("message", _POSITIVE)
def test_csg02_positives_overflow(message):
    assert _guard().check(message).decision is GuardDecision.REPRESENTATIONAL_OVERFLOW


@pytest.mark.parametrize("message", _NEGATIVE)
def test_csg02b_negatives_safe(message):
    assert _guard().check(message).decision is GuardDecision.SAFE


# =============================================
# CSG-03 — rule components
# =============================================

def test_csg03_single_product_safe():
    assert _guard().check("manda o provolone").decision is GuardDecision.SAFE


def test_csg03b_two_products_overflow():
    assert (
        _guard().check("manda provolone e brie").decision
        is GuardDecision.REPRESENTATIONAL_OVERFLOW
    )


def test_csg03c_compound_entity_overflow():
    assert (
        _guard().check("tira brie e gorgonzola").decision
        is GuardDecision.REPRESENTATIONAL_OVERFLOW
    )


def test_csg03d_two_verbs_overflow():
    assert (
        _guard().check("adiciona provolone e remove gorgonzola").decision
        is GuardDecision.REPRESENTATIONAL_OVERFLOW
    )


def test_csg03e_quantity_not_in_evidence():
    result = _guard().check("manda 5kg de provolone forma 5kg")
    assert result.decision is GuardDecision.SAFE
    assert not any("quant" in e for e in result.evidence)


# =============================================
# CSG-04 — evidence contents
# =============================================

def test_csg04_evidence_products():
    r = _guard().check("manda provolone e brie")
    assert any(e.startswith("products:") for e in r.evidence)


def test_csg04b_evidence_compound_entity():
    r = _guard().check("tira brie e gorgonzola")
    assert any(e.startswith("compound_entity:") for e in r.evidence)


def test_csg04c_evidence_operations():
    r = _guard().check("adiciona provolone e remove gorgonzola")
    assert any(e.startswith("operations:") for e in r.evidence)


def test_csg04d_safe_evidence_empty():
    assert _guard().check("manda o provolone").evidence == ()


# =============================================
# CSG-05 — fail closed
# =============================================

def test_csg05_extractor_failure_raises():
    def broken(message, labels, *, threshold=0.3):
        raise RuntimeError("boom")
    with pytest.raises(SafetyGuardFailure):
        CommandSafetyGuard(broken).check("manda brie")


def test_csg05b_guarded_fn_fails_closed():
    def broken(message, labels, *, threshold=0.3):
        raise RuntimeError("boom")

    def real_fn(message, state):
        raise AssertionError("real_fn must not be called")

    guarded = make_guarded_resolve_operation(
        CommandSafetyGuard(broken), real_fn,
    )
    result = guarded("manda brie", OrderState())
    assert result.outcome is OutcomeType.NEEDS_CLARIFICATION
    assert result.reason_code == REASON_CODE_OVERFLOW


# =============================================
# CSG-06 — make_guarded_resolve_operation
# =============================================

def test_csg06_safe_delegates():
    calls = []

    def real_fn(message, state):
        calls.append((message, state))
        return ResolutionResult(outcome=OutcomeType.NO_OP)

    guarded = make_guarded_resolve_operation(_guard(), real_fn)
    state = OrderState()
    result = guarded("manda o provolone", state)
    assert result.outcome is OutcomeType.NO_OP
    assert calls == [("manda o provolone", state)]


def test_csg06b_overflow_skips_real_fn():
    calls = []

    def real_fn(message, state):
        calls.append((message, state))
        return ResolutionResult(outcome=OutcomeType.NO_OP)

    guarded = make_guarded_resolve_operation(_guard(), real_fn)
    result = guarded("manda provolone e brie", OrderState())
    assert result.outcome is OutcomeType.NEEDS_CLARIFICATION
    assert result.reason_code == REASON_CODE_OVERFLOW
    assert calls == []


def test_csg06c_overflow_evidence_preserved():
    def real_fn(message, state):
        raise AssertionError("real_fn must not run")

    guarded = make_guarded_resolve_operation(_guard(), real_fn)
    result = guarded("manda provolone e brie", OrderState())
    assert any(e.startswith("products:") for e in result.evidence)


# =============================================
# CSG-07 — E2E overflow: no engine call
# =============================================

def test_csg07_e2e_overflow_no_engine():
    state = OrderState()
    engine = OrderEngine()
    real_calls = []

    def real_fn(message, state_arg):
        real_calls.append((message, state_arg))
        raise AssertionError("resolve_operation must not run")

    guarded = make_guarded_resolve_operation(_guard(), real_fn)

    caller_result = invoke(
        "manda provolone e brie",
        _command_observation(),
        _command_plan(),
        state,
        resolve_operation_fn=guarded,
    )

    assert caller_result.command is not None
    assert caller_result.command.outcome is OutcomeType.NEEDS_CLARIFICATION
    assert caller_result.command.reason_code == REASON_CODE_OVERFLOW

    execution = compose_command_execution(caller_result, state, engine)
    assert execution.status is CommandExecutionStatus.NOT_EXECUTABLE
    assert state.items == []
    assert real_calls == []


# =============================================
# CSG-08 — E2E safe: executes normally
# =============================================

def test_csg08_e2e_safe_executes():
    state = OrderState()
    engine = OrderEngine()

    def real_fn(message, state_arg):
        return ResolutionResult(
            outcome=OutcomeType.OPERATION,
            operation={
                "type": "ADD_ITEM",
                "product_id": "SKU-PROV",
                "product_term": "provolone",
                "quantity_value": 5.0,
                "quantity_unit": "KG",
                "target_item_id": None,
                "replacement_product_id": None,
            },
            evidence=[],
        )

    guarded = make_guarded_resolve_operation(_guard(), real_fn)

    caller_result = invoke(
        "manda o provolone",
        _command_observation(),
        _command_plan(),
        state,
        resolve_operation_fn=guarded,
    )
    assert caller_result.command is not None
    assert caller_result.command.outcome is OutcomeType.OPERATION

    execution = compose_command_execution(caller_result, state, engine)
    assert execution.status is CommandExecutionStatus.EXECUTED
    assert len(state.items) == 1
    assert state.items[0].product_id == "SKU-PROV"


# =============================================
# CSG-09 — QUERY + COMMAND independence
# =============================================

def test_csg09_query_side_runs_even_when_command_overflows():
    def fake_query(message, semantic_intent):
        return QueryResolutionResult(
            status=QueryResolutionStatus.PRODUCT_NOT_FOUND,
            query_type=QueryType.QUERY_PRICE,
            evidence=[],
        )

    def real_fn(message, state_arg):
        raise AssertionError("resolve_operation must not run")

    guarded = make_guarded_resolve_operation(_guard(), real_fn)

    obs = SignalObservation(
        query=QueryObservation(signal=QueryIntentSignal.QUERY_PRICE),
        command=CommandObservation(evidence=CommandEvidence.PRESENT),
    )
    plan = DispatchPlan(decisions=(
        DispatchDecision(DispatchTarget.QUERY, DispatchAction.DISPATCH),
        DispatchDecision(DispatchTarget.COMMAND, DispatchAction.DISPATCH),
    ))

    caller_result = invoke(
        "manda provolone e brie",
        obs, plan, OrderState(),
        resolve_query_fn=fake_query,
        resolve_operation_fn=guarded,
    )

    assert caller_result.query is not None
    assert caller_result.query.status is QueryResolutionStatus.PRODUCT_NOT_FOUND
    assert caller_result.command.outcome is OutcomeType.NEEDS_CLARIFICATION


# =============================================
# CSG-10 — dependency isolation
# =============================================

_ALLOWED_IMPORTS = {
    "__future__",
    "re",
    "dataclasses",
    "enum",
    "typing",
    "order.resolution_result",
}


def test_csg10_imports_only_expected():
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


def test_csg10b_no_adapter_or_engine_strings_in_code():
    source = _MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

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

    forbidden = (
        "ModularAdapter",
        "OrderEngine",
        "OrderState",
        "catalog_retriever",
        "product_resolver",
    )
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstring_ids
        ):
            for token in forbidden:
                assert token not in node.value, (
                    f"non-docstring string references {token!r}"
                )