from typing import Optional, Dict, Any
import re

from order.state import OrderState
from order.resolved_operation import OperationType
from order.resolution_result import ResolutionResult, OutcomeType
from order.resolution_composer import ResolutionComposer
from order.operation_resolver import (
    OperationResolver,
    OperationResolutionStatus,
    OperationSource,
)
from order.target_resolver import TargetResolver, TargetStatus
from order.pending_resolver import PendingResolver, PendingStatus
from order.catalog_retriever import CatalogRetriever
from order.product_resolver import ProductResolver
from benchmark.adapters.modular import ModularAdapter
from pipeline.reference_resolver import ReferenceResolver


_adapter = None
_resolver = None
_target_resolver = None
_pending_resolver = None
_catalog_retriever = None
_product_resolver = None
_composer = None
_operation_resolver = None


def _get_adapter():
    global _adapter
    if _adapter is None:
        _adapter = ModularAdapter()
    return _adapter


def _get_resolver():
    global _resolver
    if _resolver is None:
        _resolver = ReferenceResolver()
    return _resolver


def _get_target_resolver():
    global _target_resolver
    if _target_resolver is None:
        _target_resolver = TargetResolver()
    return _target_resolver


def _get_pending_resolver():
    global _pending_resolver
    if _pending_resolver is None:
        _pending_resolver = PendingResolver()
    return _pending_resolver


def _get_catalog_retriever():
    global _catalog_retriever
    if _catalog_retriever is None:
        _catalog_retriever = CatalogRetriever()
    return _catalog_retriever


def _get_product_resolver():
    global _product_resolver
    if _product_resolver is None:
        _product_resolver = ProductResolver()
    return _product_resolver


def _get_composer():
    global _composer
    if _composer is None:
        _composer = ResolutionComposer()
    return _composer


def _get_operation_resolver():
    global _operation_resolver
    if _operation_resolver is None:
        _operation_resolver = OperationResolver()
    return _operation_resolver


# =============================================
# Helpers
# =============================================

def _extract_replacement_term(message: str) -> Optional[str]:
    """
    Extrai o termo do produto de substituição em mensagens do tipo
    'troca X por Y', 'substitui X por Y', 'troca X pelo Y'.
    """
    msg_lower = message.lower()
    patterns = [
        r"(?:por|pelo|pela)\s+(.+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, msg_lower)
        if match:
            term = match.group(1).strip()
            term = re.sub(r"^(o|a|os|as)\s+", "", term)
            return term if term else None
    return None


def _extract_source_term(message: str, product_term: Optional[str]) -> Optional[str]:
    """
    Extrai o termo do produto de origem em mensagens do tipo 'troca X por Y'.
    """
    msg_lower = message.lower()
    if product_term and " por " in product_term.lower():
        return product_term.lower().split(" por ")[0].strip()

    match = re.search(
        r"(?:troca|substitui|substitua)\s+(?:o|a|os|as)?\s*(.+?)\s+(?:por|pelo|pela)",
        msg_lower,
    )
    if match:
        return match.group(1).strip()

    return product_term


# =============================================
# Pipeline principal
# =============================================

def resolve_operation(message: str, state: OrderState) -> ResolutionResult:
    """
    Pipeline upstream unificado: gera ResolutionResult a partir de mensagem + OrderState.
    """
    adapter = _get_adapter()
    resolver = _get_resolver()
    target_resolver = _get_target_resolver()
    pending_resolver = _get_pending_resolver()
    catalog_retriever = _get_catalog_retriever()
    product_resolver = _get_product_resolver()
    composer = _get_composer()
    operation_resolver = _get_operation_resolver()

    # 1. Reference Resolution
    ref_signal = resolver.resolve(message, state)

    # 2. NLP
    interpretation = adapter.predict(message)
    message_intent_str = interpretation.get("intent")
    product_term = interpretation.get("product_term")
    brand = interpretation.get("explicit_brand")
    presentation = interpretation.get("explicit_presentation")
    quantity = interpretation.get("quantity", {}).get("value")
    unit = interpretation.get("quantity", {}).get("unit")

    # 3. Normaliza message_intent para OperationType
    intent_map = {
        "ADD_ITEM": OperationType.ADD_ITEM,
        "REMOVE_ITEM": OperationType.REMOVE_ITEM,
        "CHANGE_QUANTITY": OperationType.CHANGE_QUANTITY,
        "REPLACE_ITEM": OperationType.REPLACE_ITEM,
        "CONFIRM_ORDER": OperationType.CONFIRM_ORDER,
        "CANCEL_ORDER": OperationType.CANCEL_ORDER,
    }
    message_intent = intent_map.get(message_intent_str, OperationType.UNKNOWN)

    # 4. PendingResolver (prioritário)
    pending_result = pending_resolver.resolve(
        message=message,
        state=state,
        semantic_signals=interpretation,
        catalog_retriever=catalog_retriever,
    )
    if pending_result.status == PendingStatus.RESOLVED:
        pending = state.pending_resolution
        return ResolutionResult(
            outcome=OutcomeType.OPERATION,
            operation={
                "type": "ADD_ITEM",
                "product_id": pending_result.resolved_product_id,
                "product_term": pending.product_term if pending else None,
                "quantity_value": pending.quantity if pending else None,
                "quantity_unit": pending.unit if pending else None,
                "target_item_id": None,
                "replacement_product_id": None,
            },
            evidence=pending_result.evidence,
        )

    # 5. OperationResolver (NOVO)
    op_resolution = operation_resolver.resolve(
        message=message,
        classifier_intent=message_intent,
    )

    if op_resolution.status == OperationResolutionStatus.AMBIGUOUS:
        return ResolutionResult(
            outcome=OutcomeType.NEEDS_CLARIFICATION,
            reason_code="AMBIGUOUS_OPERATION",
        )

    if op_resolution.resolved_operation_type is None:
        return ResolutionResult(
            outcome=OutcomeType.NEEDS_CLARIFICATION,
            reason_code="INTENT_NOT_RECOGNIZED",
        )

    op_type = op_resolution.resolved_operation_type

    # 6. Extração de source e replacement (para REPLACE_ITEM)
    source_term = product_term
    replacement_term = None
    if op_type == OperationType.REPLACE_ITEM:
        source_term = _extract_source_term(message, product_term)
        replacement_term = _extract_replacement_term(message)

    # 7. Target Resolution (source)
    target_status = None
    target_reason = None
    target_id = None
    if op_type in [
        OperationType.REMOVE_ITEM,
        OperationType.CHANGE_QUANTITY,
        OperationType.REPLACE_ITEM,
    ]:
        target_result = target_resolver.resolve(
            message=message,
            state=state,
            reference_product_term=source_term,
            ref_signal=ref_signal,
        )
        target_status = target_result.status
        target_reason = target_result.reason_code
        target_id = target_result.target_item_id

    # 8. Product Resolution
    product_status = None
    product_id = None

    if op_type == OperationType.ADD_ITEM:
        catalog_candidates = catalog_retriever.retrieve_with_constraints(
            message, brand=brand, presentation=presentation
        )
        product_status = product_resolver.resolve(
            catalog_candidates, product_term=product_term, brand=brand
        )
        if product_status == "EXACT_MATCH" and len(catalog_candidates) == 1:
            product_id = catalog_candidates[0]

    elif op_type == OperationType.REPLACE_ITEM:
        replacement_query = replacement_term or ""
        catalog_candidates = catalog_retriever.retrieve_with_constraints(
            replacement_query, brand=None, presentation=None
        )
        product_status = product_resolver.resolve(
            catalog_candidates, product_term=replacement_query, brand=None
        )
        if product_status == "EXACT_MATCH" and len(catalog_candidates) == 1:
            product_id = catalog_candidates[0]

    # 9. Pending bloqueante
    pending_blocking = (
        state.pending_resolution is not None
        and pending_result.status == PendingStatus.NOT_APPLICABLE
    )

    # 10. Composer
    clarification = composer.compose(
        op_type=op_type,
        target_status=target_status,
        target_reason=target_reason,
        product_status=product_status,
        quantity_value=quantity,
        pending_blocking=pending_blocking,
    )
    if clarification is not None:
        return clarification

    # 11. Operação válida
    operation = {
        "type": op_type.value,
        "product_id": product_id if op_type == OperationType.ADD_ITEM else None,
        "product_term": product_term,
        "target_item_id": target_id if op_type in [
            OperationType.REMOVE_ITEM,
            OperationType.CHANGE_QUANTITY,
            OperationType.REPLACE_ITEM,
        ] else None,
        "quantity_value": quantity,
        "quantity_unit": unit,
        "replacement_product_id": product_id if op_type == OperationType.REPLACE_ITEM else None,
    }
    return ResolutionResult(
        outcome=OutcomeType.OPERATION,
        operation=operation,
        evidence=["interpretation"],
    )