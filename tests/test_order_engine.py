import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from order.engine import OrderEngine
from order.state import OrderState, OrderItem
from order.resolved_operation import ResolvedOperation, OperationType
from order.pending import PendingResolution

def test_engine_confirm_empty_state():
    """Teste: confirmação de pedido vazio com status READY_TO_CONFIRM."""
    engine = OrderEngine()
    state = OrderState()
    state.status = "READY_TO_CONFIRM"
    op = ResolvedOperation(type=OperationType.CONFIRM_ORDER)
    new_state, events = engine.apply(state, op)
    assert "ORDER_CONFIRMED" in events
    assert new_state.status == "CONFIRMED"

def test_engine_confirm_with_pending():
    """Teste: confirmação com pendência ativa deve ser bloqueada."""
    engine = OrderEngine()
    state = OrderState()
    state.status = "READY_TO_CONFIRM"
    state.pending_resolution = PendingResolution(
        product_term="teste",
        missing_fields=["brand"],
        reason="AMBIGUOUS"
    )
    op = ResolvedOperation(type=OperationType.CONFIRM_ORDER)
    new_state, events = engine.apply(state, op)
    expected_msg = "Confirmação bloqueada: existe resolução pendente"
    assert expected_msg in events
    assert new_state.status != "CONFIRMED"

def test_add_item_with_product_id():
    """ADD_ITEM: com product_id → item resolvido, status READY_TO_CONFIRM."""
    engine = OrderEngine()
    state = OrderState()
    state.status = "DRAFT"
    op = ResolvedOperation(
        type=OperationType.ADD_ITEM,
        product_id="CQ-29",
        product_term="Manteiga s/sal",
        quantity_value=10.0,
        quantity_unit="KG"
    )
    new_state, events = engine.apply(state, op)
    assert "ITEM_ADDED" in events
    assert len(new_state.items) == 1
    assert new_state.items[0].resolved is True
    assert new_state.items[0].needs_clarification is False
    assert new_state.status == "READY_TO_CONFIRM"

def test_add_item_without_product_id():
    """ADD_ITEM sem product_id → rejeitado pelo contrato normativo.

    Regression guard do contrato Track 9C Stage 1A:
    product_term sozinho NÃO autoriza execução. O Engine deve rejeitar
    a operação sem produzir ITEM_ADDED, item, PendingResolution, nem
    mutação de OrderState.
    """
    engine = OrderEngine()
    state = OrderState()
    state.status = "DRAFT"
    op = ResolvedOperation(
        type=OperationType.ADD_ITEM,
        product_term="provolone",
        quantity_value=5.0,
        quantity_unit="KG"
    )

    # Contrato de execução rejeita a operação.
    assert op.is_valid() is False

    # Engine rejeita sem produzir efeito operacional.
    new_state, events = engine.apply(state, op)
    assert "Operação inválida: campos obrigatórios faltando" in events
    assert "ITEM_ADDED" not in events
    assert len(new_state.items) == 0
    assert new_state.pending_resolution is None
    assert new_state.status == "DRAFT"

def test_remove_item_existing():
    """REMOVE_ITEM: remove item existente."""
    engine = OrderEngine()
    state = OrderState()
    item = OrderItem(product_term="Manteiga s/sal", product_id="CQ-29", resolved=True)
    state.add_item(item)
    state.status = "READY_TO_CONFIRM"
    op = ResolvedOperation(
        type=OperationType.REMOVE_ITEM,
        target_item_id=item.id
    )
    new_state, events = engine.apply(state, op)
    assert "ITEM_REMOVED" in events
    assert len(new_state.items) == 0
    assert new_state.status == "DRAFT"

def test_remove_item_not_found():
    """REMOVE_ITEM: tentar remover item inexistente → erro."""
    engine = OrderEngine()
    state = OrderState()
    state.status = "DRAFT"
    op = ResolvedOperation(
        type=OperationType.REMOVE_ITEM,
        target_item_id="item_999"
    )
    new_state, events = engine.apply(state, op)
    assert "Item item_999 não encontrado" in events
    assert len(new_state.items) == 0

def test_change_quantity_existing():
    """CHANGE_QUANTITY: altera quantidade de item existente."""
    engine = OrderEngine()
    state = OrderState()
    item = OrderItem(product_term="Manteiga s/sal", quantity=10.0, unit="KG", resolved=True)
    state.add_item(item)
    state.status = "READY_TO_CONFIRM"
    op = ResolvedOperation(
        type=OperationType.CHANGE_QUANTITY,
        target_item_id=item.id,
        quantity_value=8.0,
        quantity_unit="KG"
    )
    new_state, events = engine.apply(state, op)
    assert "ITEM_QUANTITY_CHANGED" in events
    assert new_state.items[0].quantity == 8.0
    assert new_state.items[0].unit == "KG"

def test_change_quantity_without_unit():
    """CHANGE_QUANTITY com quantity_unit=None é válido (KEEP_EXISTING_UNIT).

    Contrato normativo Track 9C Stage 1A: quando a unidade não é informada
    na mensagem, quantity_unit=None é semanticamente 'manter unidade
    existente do item'. O Engine preserva a unidade do estado.
    """
    engine = OrderEngine()
    state = OrderState()
    item = OrderItem(product_term="Manteiga s/sal", quantity=10.0, unit="KG", resolved=True)
    state.add_item(item)
    state.status = "READY_TO_CONFIRM"
    op = ResolvedOperation(
        type=OperationType.CHANGE_QUANTITY,
        target_item_id=item.id,
        quantity_value=3.0,
        quantity_unit=None
    )
    assert op.is_valid() is True

    new_state, events = engine.apply(state, op)
    assert "ITEM_QUANTITY_CHANGED" in events
    assert new_state.items[0].quantity == 3.0
    assert new_state.items[0].unit == "KG"

def test_change_quantity_not_found():
    """CHANGE_QUANTITY: tentar alterar item inexistente → erro."""
    engine = OrderEngine()
    state = OrderState()
    state.status = "DRAFT"
    op = ResolvedOperation(
        type=OperationType.CHANGE_QUANTITY,
        target_item_id="item_999",
        quantity_value=5.0
    )
    new_state, events = engine.apply(state, op)
    assert "Item item_999 não encontrado" in events
    assert len(new_state.items) == 0

def test_cancel_order_from_draft():
    """CANCEL_ORDER: cancela pedido em DRAFT."""
    engine = OrderEngine()
    state = OrderState()
    state.status = "DRAFT"
    op = ResolvedOperation(type=OperationType.CANCEL_ORDER)
    new_state, events = engine.apply(state, op)
    assert "ORDER_CANCELLED" in events
    assert new_state.status == "CANCELLED"

def test_cancel_order_confirmed_blocked():
    """CANCEL_ORDER: pedido confirmado não pode ser cancelado."""
    engine = OrderEngine()
    state = OrderState()
    state.status = "CONFIRMED"
    op = ResolvedOperation(type=OperationType.CANCEL_ORDER)
    new_state, events = engine.apply(state, op)
    assert "Pedido já está CONFIRMED" in events
    assert new_state.status == "CONFIRMED"

def test_replace_item():
    """REPLACE_ITEM: substitui produto de um item."""
    engine = OrderEngine()
    state = OrderState()
    item = OrderItem(product_term="Provolone", product_id="CQ-44", resolved=True)
    state.add_item(item)
    state.status = "READY_TO_CONFIRM"
    op = ResolvedOperation(
        type=OperationType.REPLACE_ITEM,
        target_item_id=item.id,
        replacement_product_id="CQ-46",
        product_term="Provolone Riqueza de Minas"
    )
    new_state, events = engine.apply(state, op)
    assert "ITEM_REPLACED" in events
    assert new_state.items[0].product_id == "CQ-46"
    assert new_state.items[0].product_term == "Provolone Riqueza de Minas"
    assert new_state.items[0].resolved is True

def test_replace_item_not_found():
    """REPLACE_ITEM: tentar substituir item inexistente → erro."""
    engine = OrderEngine()
    state = OrderState()
    state.status = "DRAFT"
    op = ResolvedOperation(
        type=OperationType.REPLACE_ITEM,
        target_item_id="item_999",
        replacement_product_id="CQ-46"
    )
    new_state, events = engine.apply(state, op)
    assert "Item item_999 não encontrado" in events
    assert len(new_state.items) == 0

def test_update_status_to_ready():
    """Teste: após adicionar item resolvido, status deve ser READY_TO_CONFIRM."""
    engine = OrderEngine()
    state = OrderState()
    state.status = "DRAFT"
    op = ResolvedOperation(
        type=OperationType.ADD_ITEM,
        product_id="CQ-29",
        product_term="Manteiga s/sal",
        quantity_value=10.0,
        quantity_unit="KG"
    )
    new_state, _ = engine.apply(state, op)
    assert new_state.status == "READY_TO_CONFIRM"

def test_draft_with_no_items():
    """Teste: estado vazio deve permanecer DRAFT."""
    engine = OrderEngine()
    state = OrderState()
    state.status = "DRAFT"
    # Nenhuma operação aplicada, deve permanecer DRAFT
    assert state.status == "DRAFT"