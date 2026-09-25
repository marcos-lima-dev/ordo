import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from pipeline.query_intent_provider import QueryIntentSignal
from pipeline.signal_observation import (
    CommandEvidence,
    CommandObservation,
    QueryObservation,
    SignalObservation,
)


# =============================================
# SO-01 — CommandEvidence enum
# =============================================

def test_so01_command_evidence_has_exactly_three_values():
    assert {e.name for e in CommandEvidence} == {
        "PRESENT",
        "ABSENT",
        "INDETERMINATE",
    }


def test_so01b_command_evidence_values_are_exact():
    assert CommandEvidence.PRESENT.value == "PRESENT"
    assert CommandEvidence.ABSENT.value == "ABSENT"
    assert CommandEvidence.INDETERMINATE.value == "INDETERMINATE"


# =============================================
# SO-02 — CommandObservation
# =============================================

def test_so02_command_observation_present():
    obs = CommandObservation(evidence=CommandEvidence.PRESENT)
    assert obs.evidence is CommandEvidence.PRESENT


def test_so02b_command_observation_absent():
    obs = CommandObservation(evidence=CommandEvidence.ABSENT)
    assert obs.evidence is CommandEvidence.ABSENT


def test_so02c_command_observation_indeterminate():
    obs = CommandObservation(evidence=CommandEvidence.INDETERMINATE)
    assert obs.evidence is CommandEvidence.INDETERMINATE


def test_so02d_command_observation_has_only_evidence_field():
    fields = {f.name for f in CommandObservation.__dataclass_fields__.values()}
    assert fields == {"evidence"}


# =============================================
# SO-03 — QueryObservation
# =============================================

def test_so03_query_observation_price():
    obs = QueryObservation(signal=QueryIntentSignal.QUERY_PRICE)
    assert obs.signal is QueryIntentSignal.QUERY_PRICE


def test_so03b_query_observation_availability():
    obs = QueryObservation(signal=QueryIntentSignal.QUERY_AVAILABILITY)
    assert obs.signal is QueryIntentSignal.QUERY_AVAILABILITY


def test_so03c_query_observation_not_query():
    obs = QueryObservation(signal=QueryIntentSignal.NOT_QUERY)
    assert obs.signal is QueryIntentSignal.NOT_QUERY


def test_so03d_query_observation_unresolved():
    obs = QueryObservation(signal=QueryIntentSignal.UNRESOLVED)
    assert obs.signal is QueryIntentSignal.UNRESOLVED


def test_so03e_query_observation_has_only_signal_field():
    fields = {f.name for f in QueryObservation.__dataclass_fields__.values()}
    assert fields == {"signal"}


# =============================================
# SO-04 — SignalObservation combinations
# =============================================

def test_so04_query_only():
    obs = SignalObservation(
        query=QueryObservation(signal=QueryIntentSignal.QUERY_PRICE),
        command=None,
    )
    assert obs.query is not None
    assert obs.command is None


def test_so04b_command_only():
    obs = SignalObservation(
        query=None,
        command=CommandObservation(evidence=CommandEvidence.PRESENT),
    )
    assert obs.query is None
    assert obs.command is not None


def test_so04c_both_present():
    obs = SignalObservation(
        query=QueryObservation(signal=QueryIntentSignal.QUERY_AVAILABILITY),
        command=CommandObservation(evidence=CommandEvidence.PRESENT),
    )
    assert obs.query is not None
    assert obs.command is not None
    assert obs.query.signal is QueryIntentSignal.QUERY_AVAILABILITY
    assert obs.command.evidence is CommandEvidence.PRESENT


def test_so04d_neither_present():
    obs = SignalObservation()
    assert obs.query is None
    assert obs.command is None


def test_so04e_query_unresolved_with_command_present():
    """
    T10-P25 boundary: an UNRESOLVED QUERY observation and a PRESENT
    COMMAND observation coexist without collapsing.
    """
    obs = SignalObservation(
        query=QueryObservation(signal=QueryIntentSignal.UNRESOLVED),
        command=CommandObservation(evidence=CommandEvidence.PRESENT),
    )
    assert obs.query.signal is QueryIntentSignal.UNRESOLVED
    assert obs.command.evidence is CommandEvidence.PRESENT


def test_so04f_signal_observation_fields_are_exactly_two():
    fields = {f.name for f in SignalObservation.__dataclass_fields__.values()}
    assert fields == {"query", "command"}


# =============================================
# SO-05 — Immutability
# =============================================

def test_so05_command_observation_is_frozen():
    obs = CommandObservation(evidence=CommandEvidence.PRESENT)
    with pytest.raises(FrozenInstanceError):
        obs.evidence = CommandEvidence.ABSENT


def test_so05b_query_observation_is_frozen():
    obs = QueryObservation(signal=QueryIntentSignal.QUERY_PRICE)
    with pytest.raises(FrozenInstanceError):
        obs.signal = QueryIntentSignal.UNRESOLVED


def test_so05c_signal_observation_is_frozen():
    obs = SignalObservation()
    with pytest.raises(FrozenInstanceError):
        obs.query = QueryObservation(signal=QueryIntentSignal.QUERY_PRICE)


# =============================================
# SO-06 — No COMMAND intent carried
# =============================================

def test_so06_no_command_intent_field_in_command_observation():
    for f in CommandObservation.__dataclass_fields__.values():
        assert f.name == "evidence"
    # And no field carries an OperationType-like value.
    obs = CommandObservation(evidence=CommandEvidence.PRESENT)
    assert set(vars(obs).keys()) == {"evidence"}


def test_so06b_signal_observation_carries_no_command_intent():
    obs = SignalObservation(
        command=CommandObservation(evidence=CommandEvidence.PRESENT),
    )
    assert set(vars(obs).keys()) == {"query", "command"}
    assert set(vars(obs.command).keys()) == {"evidence"}


# =============================================
# SO-07 — No dispatch/resolution/execution authority
# =============================================

def test_so07_no_dispatch_authority_methods():
    forbidden_names = (
        "dispatch",
        "route",
        "plan",
        "authorize",
        "execute",
        "apply",
        "resolve",
        "observe",
    )
    for cls in (
        CommandEvidence,
        CommandObservation,
        QueryObservation,
        SignalObservation,
    ):
        for name in forbidden_names:
            assert not hasattr(cls, name), (
                f"{cls.__name__} must not expose {name!r}"
            )


# =============================================
# SO-08 — Dependency isolation (source inspection)
# =============================================

def test_so08_module_does_not_import_forbidden_modules():
    source = (
        Path(__file__).parent.parent
        / "pipeline"
        / "signal_observation.py"
    ).read_text(encoding="utf-8")
    forbidden_imports = (
        "benchmark.adapters",
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
        "pipeline.query_intent_bootstrap",
    )
    for token in forbidden_imports:
        assert token not in source, (
            f"signal_observation.py must not import {token}"
        )


def test_so08b_module_imports_query_intent_signal():
    source = (
        Path(__file__).parent.parent
        / "pipeline"
        / "signal_observation.py"
    ).read_text(encoding="utf-8")
    assert "from pipeline.query_intent_provider import QueryIntentSignal" in source


# =============================================
# SO-09 — Equality (dataclass semantics)
# =============================================

def test_so09_command_observation_equality():
    a = CommandObservation(evidence=CommandEvidence.PRESENT)
    b = CommandObservation(evidence=CommandEvidence.PRESENT)
    c = CommandObservation(evidence=CommandEvidence.ABSENT)
    assert a == b
    assert a != c


def test_so09b_signal_observation_equality():
    a = SignalObservation(
        query=QueryObservation(signal=QueryIntentSignal.QUERY_PRICE),
    )
    b = SignalObservation(
        query=QueryObservation(signal=QueryIntentSignal.QUERY_PRICE),
    )
    c = SignalObservation()
    assert a == b
    assert a != c