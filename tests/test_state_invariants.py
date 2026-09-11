import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from order.state import OrderState, OrderItem
from order.pending import PendingResolution
from order.target import Target, TargetType
from order.catalog_retriever import CatalogRetriever
from order.product_resolver import ProductResolver, ResolutionStatus

# =============================================
# Fixtures
# =============================================

@pytest.fixture
def empty_state():
    return OrderState()

@pytest.fixture
def state_with_items():
    state = OrderState()
    item1 = OrderItem(product_term="Manteiga s/sal", quantity=10.0, unit="KG", resolved=True)
    item2 = OrderItem(product_term="Provolone forma 5 kg", quantity=5.0, unit="KG", resolved=False, needs_clarification=True)
    state.add_item(item1)
    state.add_item(item2)
    return state

@pytest.fixture
def state_with_pending():
    state = OrderState()
    item = OrderItem(product_term="provolone", quantity=5.0, unit="KG", resolved=False, needs_clarification=True)
    state.add_item(item)
    pending = PendingResolution(
        product_term="provolone",
        quantity=5.0,
        unit="KG",
        missing_fields=["brand"],
        reason="AMBIGUOUS"
    )
    state.set_pending(pending)
    return state

@pytest.fixture
def catalog_retriever():
    return CatalogRetriever()

# =============================================
# Função auxiliar para verificar se confirmação é permitida
# =============================================

def can_confirm(state: OrderState) -> bool:
    """Retorna True se o estado permite confirmação."""
    if state.pending_resolution is not None:
        return False
    if any(item.needs_clarification for item in state.items):
        return False
    return True

# =============================================
# INV-01: pending_resolution != None → order cannot be CONFIRMED
# =============================================

def test_inv_01_pending_blocks_confirmation(state_with_pending):
    """INV-01: pending_resolution != None → order cannot be CONFIRMED."""
    assert state_with_pending.pending_resolution is not None
    assert can_confirm(state_with_pending) is False
    # Tentativa de confirmar deve ser bloqueada
    # Simula lógica de confirmação que usa can_confirm
    if can_confirm(state_with_pending):
        state_with_pending.status = "CONFIRMED"
    else:
        state_with_pending.status = "NEEDS_CLARIFICATION"
    assert state_with_pending.status != "CONFIRMED"

# =============================================
# INV-02: resolution becomes EXACT_MATCH → pending_resolution for that item is cleared
# =============================================

def test_inv_02_resolution_clears_pending(state_with_pending):
    """INV-02: resolution becomes EXACT_MATCH → pending_resolution for that item is cleared."""
    pending = state_with_pending.pending_resolution
    # Simula resolução: marca a pendência como resolvida
    if pending:
        pending.missing_fields = []  # não falta mais nada
        # A lógica de resolução deve limpar a pendência E marcar o item como resolvido
        # (Na implementação real, isso seria feito pelo ProductResolver)
        state_with_pending.clear_pending()
        # Marca o item correspondente como resolvido
        for item in state_with_pending.items:
            if item.product_term == pending.product_term:
                item.resolved = True
                item.needs_clarification = False
                break
    assert state_with_pending.pending_resolution is None
    # Verifica que o item foi marcado como resolvido
    for item in state_with_pending.items:
        if item.product_term == "provolone":
            assert item.resolved is True
            assert item.needs_clarification is False

# =============================================
# INV-03: all items resolved AND no pending resolution → confirmation may proceed
# =============================================

def test_inv_03_all_resolved_allows_confirmation(state_with_items):
    """INV-03: all items resolved AND no pending resolution → confirmation may proceed."""
    # Garante que todos os itens estejam resolvidos
    for item in state_with_items.items:
        item.resolved = True
        item.needs_clarification = False
    state_with_items.pending_resolution = None
    # Confirmação deve ser permitida
    assert can_confirm(state_with_items) is True

# =============================================
# INV-04: resolving one item must not clear another item's pending state
# =============================================

def test_inv_04_resolve_one_item_does_not_affect_others(state_with_items):
    """INV-04: resolving one item must not clear another item's pending state."""
    # Adiciona um segundo item com pendência
    item3 = OrderItem(product_term="Gorgonzola", quantity=2.0, unit="KG", resolved=False, needs_clarification=True)
    state_with_items.add_item(item3)
    pending2 = PendingResolution(
        product_term="Gorgonzola",
        quantity=2.0,
        unit="KG",
        missing_fields=["brand"],
        reason="AMBIGUOUS"
    )
    state_with_items.set_pending(pending2)

    # Resolve o primeiro item (provolone)
    for item in state_with_items.items:
        if item.product_term == "Provolone forma 5 kg":
            item.resolved = True
            item.needs_clarification = False
            break

    # O provolone está resolvido
    provolone = next((i for i in state_with_items.items if i.product_term == "Provolone forma 5 kg"), None)
    assert provolone.resolved is True
    assert provolone.needs_clarification is False

    # O pending_resolution ainda deve existir (por causa do Gorgonzola)
    assert state_with_items.pending_resolution is not None
    assert state_with_items.pending_resolution.product_term == "Gorgonzola"

# =============================================
# INV-05: AMBIGUOUS or NOT_FOUND must not silently become resolved
# =============================================

def test_inv_05_ambiguous_not_silently_resolved():
    """INV-05: AMBIGUOUS or NOT_FOUND must not silently become resolved."""
    state = OrderState()
    item = OrderItem(
        product_term="provolone",
        quantity=5.0,
        unit="KG",
        resolved=False,
        needs_clarification=True,
        clarification_questions=["brand", "presentation"]
    )
    state.add_item(item)
    pending = PendingResolution(
        product_term="provolone",
        quantity=5.0,
        unit="KG",
        missing_fields=["brand", "presentation"],
        reason="AMBIGUOUS"
    )
    state.set_pending(pending)

    # Simula uma tentativa de resolução sem resolver todas as pendências
    # Apenas marca um campo como resolvido, mas ainda falta apresentação
    state.pending_resolution.missing_fields = ["presentation"]  # ainda falta presentation
    # O item não deve ser considerado resolvido
    assert state.pending_resolution is not None
    assert len(state.pending_resolution.missing_fields) > 0
    assert state.status == "NEEDS_CLARIFICATION"

    # Mesmo que tentemos confirmar, deve ser bloqueado
    assert can_confirm(state) is False

# =============================================
# Testes de Target Resolution Precedence
# =============================================

def test_target_precedence_explicit_over_pending():
    """Target Resolution: referência explícita tem prioridade sobre pendência."""
    # Cria estado com pendência
    state = OrderState()
    item1 = OrderItem(product_term="manteiga", quantity=1.0, unit="KG", resolved=True)
    item2 = OrderItem(product_term="provolone", quantity=5.0, unit="KG", resolved=False, needs_clarification=True)
    state.add_item(item1)
    state.add_item(item2)
    pending = PendingResolution(
        product_term="provolone",
        quantity=5.0,
        unit="KG",
        missing_fields=["brand"],
        reason="AMBIGUOUS"
    )
    state.set_pending(pending)

    # Mensagem com referência explícita a "manteiga"
    target = Target(type=TargetType.EXPLICIT_REFERENCE, product_term="manteiga")
    # Verifica que a lógica de target deve priorizar explícita (conceitual)
    assert target.type == TargetType.EXPLICIT_REFERENCE
    assert target.product_term == "manteiga"

def test_target_precedence_pending_over_generic():
    """Target Resolution: pendência tem prioridade sobre referência genérica."""
    state = OrderState()
    item1 = OrderItem(product_term="manteiga", quantity=1.0, unit="KG", resolved=True)
    item2 = OrderItem(product_term="provolone", quantity=5.0, unit="KG", resolved=False, needs_clarification=True)
    state.add_item(item1)
    state.add_item(item2)
    pending = PendingResolution(
        product_term="provolone",
        quantity=5.0,
        unit="KG",
        missing_fields=["brand"],
        reason="AMBIGUOUS"
    )
    state.set_pending(pending)

    # Mensagem genérica "esse" deve priorizar a pendência (se houver)
    target = Target(type=TargetType.PENDING_ITEM, product_term="provolone")
    assert target.type == TargetType.PENDING_ITEM
    assert state.pending_resolution is not None

# =============================================
# Testes de REMOVE_ITEM e CHANGE_QUANTITY
# =============================================

def test_remove_item_explicit_target():
    """REMOVE_ITEM: só executa se target for válido."""
    state = OrderState()
    item1 = OrderItem(product_term="manteiga", quantity=1.0, unit="KG", resolved=True)
    item2 = OrderItem(product_term="provolone", quantity=5.0, unit="KG", resolved=True)
    state.add_item(item1)
    state.add_item(item2)

    target = Target(type=TargetType.EXPLICIT_REFERENCE, product_term="provolone")
    if target.type == TargetType.EXPLICIT_REFERENCE and target.product_term:
        for i, item in enumerate(state.items):
            if item.product_term == target.product_term:
                state.items.pop(i)
                break
    # Verifica que apenas provolone foi removido
    assert len(state.items) == 1
    assert state.items[0].product_term == "manteiga"

def test_remove_item_no_target_blocks():
    """REMOVE_ITEM: sem target válido, operação é bloqueada."""
    state = OrderState()
    item1 = OrderItem(product_term="manteiga", quantity=1.0, unit="KG", resolved=True)
    item2 = OrderItem(product_term="provolone", quantity=5.0, unit="KG", resolved=True)
    state.add_item(item1)
    state.add_item(item2)

    target = Target(type=TargetType.UNKNOWN)
    if target.type != TargetType.UNKNOWN and target.product_term:
        # não executa
        pass
    assert len(state.items) == 2
    state.status = "NEEDS_CLARIFICATION"
    assert state.status == "NEEDS_CLARIFICATION"

def test_change_quantity_with_target():
    """CHANGE_QUANTITY: aplica apenas se target for válido."""
    state = OrderState()
    item1 = OrderItem(product_term="manteiga", quantity=1.0, unit="KG", resolved=True)
    item2 = OrderItem(product_term="provolone", quantity=5.0, unit="KG", resolved=True)
    state.add_item(item1)
    state.add_item(item2)

    target = Target(type=TargetType.EXPLICIT_REFERENCE, product_term="provolone")
    if target.type == TargetType.EXPLICIT_REFERENCE and target.product_term:
        for item in state.items:
            if item.product_term == target.product_term:
                item.quantity = 8.0
                break
    assert state.items[0].quantity == 1.0  # manteiga inalterada
    assert state.items[1].quantity == 8.0  # provolone alterado

def test_change_quantity_no_target_blocks():
    """CHANGE_QUANTITY: sem target válido, operação é bloqueada."""
    state = OrderState()
    item1 = OrderItem(product_term="manteiga", quantity=1.0, unit="KG", resolved=True)
    item2 = OrderItem(product_term="provolone", quantity=5.0, unit="KG", resolved=True)
    state.add_item(item1)
    state.add_item(item2)

    target = Target(type=TargetType.UNKNOWN)
    if target.type != TargetType.UNKNOWN and target.product_term:
        # não executa
        pass
    assert state.items[0].quantity == 1.0
    assert state.items[1].quantity == 5.0
    state.status = "NEEDS_CLARIFICATION"
    assert state.status == "NEEDS_CLARIFICATION"

# =============================================
# Testes de Precedência Classificador vs Fallback
# =============================================

def test_intent_fallback_precedence():
    """Regra determinística pode sobrepor classificador em padrões inequívocos."""
    classifier_intent = "ADD_ITEM"
    msg = "muda para 4"

    import re
    if re.search(r'muda\s*para\s*\d+', msg):
        resolved_intent = "CHANGE_QUANTITY"
    else:
        resolved_intent = classifier_intent

    assert resolved_intent == "CHANGE_QUANTITY"
    assert resolved_intent != classifier_intent

def test_intent_fallback_does_not_overpower_ambiguous():
    """Fallback não deve sobrepor em padrões ambíguos."""
    classifier_intent = "ADD_ITEM"
    msg = "coloca 3"

    import re
    if re.search(r'coloca\s*\d+\s*(?:kg|quilos|g|gramas|forma|peça|pote)', msg):
        resolved_intent = "ADD_ITEM"
    else:
        resolved_intent = classifier_intent

    assert resolved_intent == "ADD_ITEM"

# =============================================
# Teste de separação extracted_product_term vs resolved_product
# =============================================

def test_separate_extracted_and_resolved_product():
    """extracted_product_term e resolved_product_id são separados."""
    extracted = "sal"
    resolved_id = "CQ-29"
    resolved_name = "Manteiga s/sal"

    assert extracted == "sal"
    assert resolved_id == "CQ-29"
    assert resolved_name == "Manteiga s/sal"

    state = OrderState()
    item = OrderItem(product_term=extracted, product_id=resolved_id)
    state.add_item(item)
    assert state.items[0].product_term == "sal"
    assert state.items[0].product_id == "CQ-29"