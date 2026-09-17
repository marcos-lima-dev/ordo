from typing import Optional, Dict, Any

from order.state import OrderState
from order.resolved_operation import OperationType
from order.resolution_result import ResolutionResult, OutcomeType
from order.resolution_composer import ResolutionComposer
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


def resolve_operation(message: str, state: OrderState) -> ResolutionResult:
    """
    Pipeline upstream unificado: gera ResolutionResult a partir de mensagem + OrderState.
    Usado tanto pelo benchmark quanto pelo diagnóstico para garantir concordância.
    """
    adapter = _get_adapter()
    resolver = _get_resolver()
    target_resolver = _get_target_resolver()
    pending_resolver = _get_pending_resolver()
    catalog_retriever = _get_catalog_retriever()
    product_resolver = _get_product_resolver()
    composer = _get_composer()

    # 1. Reference Resolution
    ref_signal = resolver.resolve(message, state)

    # 2. NLP
    interpretation = adapter.predict(message)
    intent = interpretation.get("intent")
    product_term = interpretation.get("product_term")
    brand = interpretation.get("explicit_brand")
    presentation = interpretation.get("explicit_presentation")
    quantity = interpretation.get("quantity", {}).get("value")
    unit = interpretation.get("quantity", {}).get("unit")

    # 3. PendingResolver (prioritário)
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

    # 4. Intent
    intent_map = {
        "ADD_ITEM": OperationType.ADD_ITEM,
        "REMOVE_ITEM": OperationType.REMOVE_ITEM,
        "CHANGE_QUANTITY": OperationType.CHANGE_QUANTITY,
        "REPLACE_ITEM": OperationType.REPLACE_ITEM,
        "CONFIRM_ORDER": OperationType.CONFIRM_ORDER,
        "CANCEL_ORDER": OperationType.CANCEL_ORDER,
    }
    op_type = intent_map.get(intent)
    if op_type is None:
        return ResolutionResult(
            outcome=OutcomeType.NEEDS_CLARIFICATION,
            reason_code="INTENT_NOT_RECOGNIZED",
        )

    # 5. Target Resolution
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
            reference_product_term=product_term,
            ref_signal=ref_signal,
        )
        target_status = target_result.status
        target_reason = target_result.reason_code
        target_id = target_result.target_item_id

    # 6. Product Resolution
    product_status = None
    product_id = None
    if op_type in [OperationType.ADD_ITEM, OperationType.REPLACE_ITEM]:
        catalog_candidates = catalog_retriever.retrieve_with_constraints(
            message, brand=brand, presentation=presentation
        )
        product_status = product_resolver.resolve(
            catalog_candidates, product_term=product_term, brand=brand
        )
        if product_status == "EXACT_MATCH" and len(catalog_candidates) == 1:
            product_id = catalog_candidates[0]

    # 7. Pending bloqueante
    pending_blocking = (
        state.pending_resolution is not None
        and pending_result.status == PendingStatus.NOT_APPLICABLE
    )

    # 8. Composer
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

    # 9. Operação válida
    operation = {
        "type": op_type.value,
        "product_id": product_id,
        "product_term": product_term,
        "target_item_id": target_id,
        "quantity_value": quantity,
        "quantity_unit": unit,
        "replacement_product_id": product_id if op_type == OperationType.REPLACE_ITEM else None,
    }
    return ResolutionResult(
        outcome=OutcomeType.OPERATION,
        operation=operation,
        evidence=["interpretation"],
    )