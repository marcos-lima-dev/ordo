import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import MagicMock

from order.engine import OrderEngine
from order.execution import execute_resolution
from order.resolution_result import ResolutionResult, OutcomeType
from order.state import OrderState, OrderItem


# =============================================
# Helpers
# =============================================

def op_result(op_dict, evidence=None):
    return ResolutionResult(
        outcome=OutcomeType.OPERATION,
        operation=op_dict,
        evidence=evidence or [],
    )


def clarify_result(reason_code="AMBIGUOUS_PRODUCT"):
    return ResolutionResult(
        outcome=OutcomeType.NEEDS_CLARIFICATION,
        operation=None,
        reason_code=reason_code,
    )


# =============================================
# E1 — executable result → boundary → Engine
# =============================================

def test_e1_executable_result_calls_engine():
    state = OrderState()
    state.status = "DRAFT"
    result = op_result({
        "type": "ADD_ITEM",
        "product_id": "CQ-29",
        "product_term": "Manteiga s/sal",
        "quantity_value": 10.0,
        "quantity_unit": "KG",
    })
    engine = OrderEngine()
    new_state, events = execute_resolution(state, result, engine)
    assert "ITEM_ADDED" in events
    assert len(new_state.items) == 1
    assert new_state.items[0].product_id == "CQ-29"


# =============================================
# E2 — NEEDS_CLARIFICATION → boundary None → Engine NOT called
# =============================================

def test_e2_needs_clarification_does_not_call_engine():
    state = OrderState()
    state.status = "DRAFT"
    result = clarify_result("AMBIGUOUS_PRODUCT")
    engine = MagicMock(spec=OrderEngine)

    new_state, events = execute_resolution(state, result, engine)

    engine.apply.assert_not_called()
    assert new_state is state
    assert events == []


# =============================================
# E3 — partial ADD → boundary None → Engine NOT called
# =============================================

def test_e3_partial_add_does_not_call_engine():
    state = OrderState()
    state.status = "DRAFT"
    result = op_result({
        "type": "ADD_ITEM",
        "product_id": None,
        "product_term": "provolone",
        "quantity_value": 5.0,
        "quantity_unit": "KG",
    })
    engine = MagicMock(spec=OrderEngine)

    new_state, events = execute_resolution(state, result, engine)

    engine.apply.assert_not_called()
    assert new_state is state
    assert events == []


# =============================================
# E4 — UNKNOWN → boundary None → Engine NOT called
# =============================================

def test_e4_unknown_does_not_call_engine():
    state = OrderState()
    state.status = "DRAFT"
    result = op_result({"type": "UNKNOWN"})
    engine = MagicMock(spec=OrderEngine)

    new_state, events = execute_resolution(state, result, engine)

    engine.apply.assert_not_called()
    assert new_state is state
    assert events == []


# =============================================
# E5 — CHANGE_QUANTITY unit=None → KEEP_EXISTING_UNIT (end-to-end)
# =============================================

def test_e5_change_quantity_unit_none_keeps_existing_unit():
    state = OrderState()
    state.status = "READY_TO_CONFIRM"
    item = OrderItem(
        product_term="Manteiga s/sal",
        quantity=5.0,
        unit="KG",
        resolved=True,
    )
    state.add_item(item)
    target_id = item.id

    result = op_result({
        "type": "CHANGE_QUANTITY",
        "target_item_id": target_id,
        "quantity_value": 3.0,
        "quantity_unit": None,
    })
    engine = OrderEngine()
    new_state, events = execute_resolution(state, result, engine)

    assert "ITEM_QUANTITY_CHANGED" in events
    assert new_state.items[0].quantity == 3.0
    assert new_state.items[0].unit == "KG"


# =============================================
# E6 — no fabricated metadata
# =============================================

def test_e6_no_fabricated_metadata():
    """A execução não deve criar source_message_id nem evidence."""
    class RecordingEngine(OrderEngine):
        def __init__(self):
            super().__init__()
            self.received = []

        def apply(self, state, operation):
            self.received.append(operation)
            return super().apply(state, operation)

    state = OrderState()
    state.status = "DRAFT"
    result = op_result(
        {
            "type": "ADD_ITEM",
            "product_id": "CQ-29",
            "product_term": "Manteiga s/sal",
        },
        evidence=["some_resolution_evidence"],  # NÃO deve ser propagado
    )
    engine = RecordingEngine()
    execute_resolution(state, result, engine)

    assert len(engine.received) == 1
    op = engine.received[0]
    assert op.source_message_id is None
    assert op.evidence == []


# =============================================
# Wrapper usa a boundary oficial
# =============================================

def test_wrapper_uses_official_boundary(monkeypatch):
    """Prova que execute_resolution chama to_resolved_operation."""
    import order.execution as ex

    spy = MagicMock(return_value=None)
    monkeypatch.setattr(ex, "to_resolved_operation", spy)

    state = OrderState()
    result = op_result({"type": "CONFIRM_ORDER"})
    engine = MagicMock(spec=OrderEngine)

    ex.execute_resolution(state, result, engine)

    spy.assert_called_once_with(result)
    engine.apply.assert_not_called()


# =============================================
# Integração — pipeline → boundary → Engine
# =============================================

def test_integration_pipeline_to_boundary_to_engine(monkeypatch):
    """Fecha a cadeia: pipeline.resolve_operation → execute_resolution → Engine."""
    from pipeline import resolution_pipeline as rp

    class StubAdapter:
        def predict(self, message):
            return {
                "intent": "CONFIRM_ORDER",
                "product_term": None,
                "explicit_brand": None,
                "explicit_presentation": None,
                "quantity": {"value": None, "unit": None},
                "catalog_candidates": [],
                "product_resolution_status": "NOT_FOUND",
            }

    monkeypatch.setattr(rp, "_adapter", StubAdapter())

    state = OrderState()
    state.status = "READY_TO_CONFIRM"

    result = rp.resolve_operation("pode fechar", state)
    assert result.outcome.value == "OPERATION"
    assert result.operation is not None
    assert result.operation["type"] == "CONFIRM_ORDER"

    engine = OrderEngine()
    new_state, events = execute_resolution(state, result, engine)
    assert new_state.status == "CONFIRMED"
    assert "ORDER_CONFIRMED" in events