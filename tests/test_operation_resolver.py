import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from order.operation_resolver import OperationResolver, OperationResolutionStatus, OperationSource
from order.resolved_operation import OperationType


@pytest.fixture
def resolver():
    return OperationResolver()


def test_tira_override_add(resolver):
    r = resolver.resolve("tira uma", OperationType.ADD_ITEM)
    assert r.resolved_operation_type == OperationType.REMOVE_ITEM
    assert r.source == OperationSource.DETERMINISTIC_SIGNAL


def test_muda_para_override_add(resolver):
    r = resolver.resolve("muda para 4", OperationType.ADD_ITEM)
    assert r.resolved_operation_type == OperationType.CHANGE_QUANTITY
    assert r.source == OperationSource.DETERMINISTIC_SIGNAL


def test_troca_confirm_classifier(resolver):
    r = resolver.resolve("troca o provolone por gorgonzola", OperationType.REPLACE_ITEM)
    assert r.resolved_operation_type == OperationType.REPLACE_ITEM
    assert r.source == OperationSource.CLASSIFIER_PLUS_CONTEXT


def test_coloca_3_keeps_add(resolver):
    r = resolver.resolve("coloca 3", OperationType.ADD_ITEM)
    assert r.resolved_operation_type == OperationType.ADD_ITEM
    assert r.source == OperationSource.CLASSIFIER_PLUS_CONTEXT


def test_unknown_classifier_with_deterministic(resolver):
    r = resolver.resolve("tira o provolone", OperationType.UNKNOWN)
    assert r.resolved_operation_type == OperationType.REMOVE_ITEM
    assert r.source == OperationSource.DETERMINISTIC_SIGNAL


def test_confirm_order(resolver):
    r = resolver.resolve("pode fechar", OperationType.CONFIRM_ORDER)
    assert r.resolved_operation_type == OperationType.CONFIRM_ORDER


def test_cancel_order(resolver):
    r = resolver.resolve("cancela tudo", OperationType.CANCEL_ORDER)
    assert r.resolved_operation_type == OperationType.CANCEL_ORDER


def test_conflicting_signals(resolver):
    r = resolver.resolve("tira e depois coloca", OperationType.ADD_ITEM)
    assert r.status == OperationResolutionStatus.AMBIGUOUS
    assert r.resolved_operation_type is None


def test_no_deterministic_signal(resolver):
    r = resolver.resolve("bom dia", OperationType.UNKNOWN)
    assert r.resolved_operation_type == OperationType.UNKNOWN
    assert r.source == OperationSource.CLASSIFIER