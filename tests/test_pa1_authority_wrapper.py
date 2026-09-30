"""
PA-1 Authority Wrapper tests.

Covers PA-1 Policy Slice v0 as implemented at the resolution boundary:
  ABSENT                -> delegate unchanged
  SINGLE + EXISTS       -> delegate with pre_resolved_product_id
  SINGLE + NOT_EXISTS   -> NEEDS_CLARIFICATION
  SINGLE + UNVERIFIABLE -> NEEDS_CLARIFICATION
  MULTIPLE              -> NEEDS_CLARIFICATION

Also asserts Safety dominance: when the CommandSafetyGuard wraps the
PA-1 wrapper, Safety short-circuits before PA-1 is consulted.
"""
import inspect
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from order.resolution_result import ResolutionResult, OutcomeType
from order.state import OrderState

from pipeline.pa1_authority import make_pa1_authority_wrapper


class _SpyRealFn:
    """Records every call. Accepts the PA-1 kwarg."""
    def __init__(self):
        self.calls = []

    def __call__(self, message, state, *, pre_resolved_product_id=None):
        self.calls.append({
            "message": message,
            "state": state,
            "pre_resolved_product_id": pre_resolved_product_id,
        })
        return ResolutionResult(
            outcome=OutcomeType.OPERATION,
            operation={
                "type": "ADD_ITEM",
                "product_id": pre_resolved_product_id,
            },
            evidence=["spy"],
        )


# ============================================
# ABSENT -> DELEGATE
# ============================================

def test_absent_delegates_unchanged():
    spy = _SpyRealFn()
    wrapped = make_pa1_authority_wrapper(spy)
    state = OrderState()
    result = wrapped("manda queijo", state)

    assert len(spy.calls) == 1
    assert spy.calls[0]["message"] == "manda queijo"
    assert spy.calls[0]["state"] is state
    assert spy.calls[0]["pre_resolved_product_id"] is None
    assert result.outcome == OutcomeType.OPERATION


# ============================================
# SINGLE + EXISTS
# ============================================

def test_single_exists_passes_canonical_identifier():
    spy = _SpyRealFn()
    wrapped = make_pa1_authority_wrapper(spy)
    result = wrapped("manda o CQ-44", OrderState())

    assert len(spy.calls) == 1
    assert spy.calls[0]["pre_resolved_product_id"] == "CQ-44"
    assert result.outcome == OutcomeType.OPERATION
    assert result.operation["product_id"] == "CQ-44"


@pytest.mark.parametrize("raw_input,expected_canonical", [
    ("manda o CQ-44",  "CQ-44"),
    ("manda o cq-44",  "CQ-44"),
    ("manda o CQ44",   "CQ-44"),
    ("manda o CQ 44",  "CQ-44"),
])
def test_single_exists_canonicalizes_all_accepted_forms(raw_input, expected_canonical):
    spy = _SpyRealFn()
    wrapped = make_pa1_authority_wrapper(spy)
    wrapped(raw_input, OrderState())

    assert spy.calls[0]["pre_resolved_product_id"] == expected_canonical


# ============================================
# SINGLE + NOT_EXISTS
# ============================================

def test_single_not_exists_short_circuits():
    spy = _SpyRealFn()
    wrapped = make_pa1_authority_wrapper(spy)
    result = wrapped("manda o CQ-99", OrderState())

    assert len(spy.calls) == 0, "real_fn must not be called on NOT_EXISTS"
    assert result.outcome == OutcomeType.NEEDS_CLARIFICATION
    assert result.reason_code == "IDENTIFIER_NOT_FOUND"
    assert "CQ-99" in result.evidence


# ============================================
# SINGLE + UNVERIFIABLE
# ============================================

def test_single_unverifiable_short_circuits():
    import pipeline.pa1_verifier as verifier_mod

    def broken_verify(raws, catalog=None):
        return [
            verifier_mod.PA1Verification(
                occurrence_raw=r, status=verifier_mod.UNVERIFIABLE,
            )
            for r in raws
        ]

    spy = _SpyRealFn()
    wrapped = make_pa1_authority_wrapper(spy, verify_fn=broken_verify)
    result = wrapped("manda o CQ-44", OrderState())

    assert len(spy.calls) == 0
    assert result.outcome == OutcomeType.NEEDS_CLARIFICATION
    assert result.reason_code == "IDENTIFIER_UNVERIFIABLE"


# ============================================
# MULTIPLE
# ============================================

def test_multiple_short_circuits():
    spy = _SpyRealFn()
    wrapped = make_pa1_authority_wrapper(spy)
    result = wrapped("manda CQ-44 e CQ-46", OrderState())

    assert len(spy.calls) == 0
    assert result.outcome == OutcomeType.NEEDS_CLARIFICATION
    assert result.reason_code == "MULTIPLE_IDENTIFIERS"
    assert "CQ-44" in result.evidence
    assert "CQ-46" in result.evidence


def test_multiple_does_not_collapse_duplicates():
    spy = _SpyRealFn()
    wrapped = make_pa1_authority_wrapper(spy)
    result = wrapped("CQ-44 e CQ-44", OrderState())

    assert len(spy.calls) == 0
    assert result.reason_code == "MULTIPLE_IDENTIFIERS"


# ============================================
# Isolation
# ============================================

def test_wrapper_module_does_not_import_execution():
    import pipeline.pa1_authority as mod
    source = inspect.getsource(mod)
    forbidden = [
        "command_execution",
        "OrderEngine",
        "execute_resolution",
        "to_resolved_operation",
        "order.engine",
    ]
    for name in forbidden:
        assert name not in source, f"wrapper must not reference {name}"


# ============================================
# Safety dominance
# ============================================

def test_safety_dominates_pa1_when_overflow():
    """
    When CommandSafetyGuard detects representational overflow, it must
    short-circuit before PA-1 Authority is consulted, even if the
    message contains a valid PA-1 identifier.
    """
    from pipeline.command_safety_guard import (
        make_guarded_resolve_operation,
        GuardDecision,
    )

    class StubOverflowGuard:
        def check(self, message):
            return SimpleNamespace(
                decision=GuardDecision.REPRESENTATIONAL_OVERFLOW,
                evidence=("stub_overflow",),
            )

    spy = _SpyRealFn()
    pa1_wrapped = make_pa1_authority_wrapper(spy)
    guarded = make_guarded_resolve_operation(StubOverflowGuard(), pa1_wrapped)

    result = guarded("manda o CQ-44", OrderState())

    assert len(spy.calls) == 0, (
        "Safety must short-circuit before PA-1 Authority is consulted"
    )
    assert result.outcome == OutcomeType.NEEDS_CLARIFICATION


def test_safety_passes_through_to_pa1_on_safe():
    """
    When the guard does not detect overflow, PA-1 Authority runs.
    """
    from pipeline.command_safety_guard import (
        make_guarded_resolve_operation,
        GuardDecision,
    )

    class StubSafeGuard:
        def check(self, message):
            return SimpleNamespace(decision=GuardDecision.SAFE, evidence=())

    spy = _SpyRealFn()
    pa1_wrapped = make_pa1_authority_wrapper(spy)
    guarded = make_guarded_resolve_operation(StubSafeGuard(), pa1_wrapped)

    guarded("manda o CQ-44", OrderState())
    assert len(spy.calls) == 1
    assert spy.calls[0]["pre_resolved_product_id"] == "CQ-44"


# ============================================
# resolve_operation kwarg — backward compatibility
# ============================================

def test_resolve_operation_accepts_pre_resolved_kwarg():
    from pipeline.resolution_pipeline import resolve_operation
    result = resolve_operation(
        "manda o CQ-44", OrderState(), pre_resolved_product_id="CQ-44",
    )
    assert result is not None


def test_resolve_operation_default_kwarg_is_backward_compatible():
    from pipeline.resolution_pipeline import resolve_operation
    result = resolve_operation("manda o CQ-44", OrderState())
    assert result is not None