import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from order.resolved_query import QueryType, ResolvedQuery
from order.resolved_operation import OperationType

_MODULE_PATH = Path(__file__).parent.parent / "order" / "resolved_query.py"


@pytest.fixture(scope="module")
def resolved_query_source():
    return _MODULE_PATH.read_text(encoding="utf-8")


# =============================================
# INVARIANT — QueryType independent from OperationType
# =============================================

def test_query_type_covers_price_and_availability():
    assert QueryType.QUERY_PRICE.value == "QUERY_PRICE"
    assert QueryType.QUERY_AVAILABILITY.value == "QUERY_AVAILABILITY"


def test_query_type_members_are_disjoint_from_operation_type():
    """No shared value between QueryType and OperationType (T10-P2)."""
    query_values = {q.value for q in QueryType}
    operation_values = {o.value for o in OperationType}
    assert query_values.isdisjoint(operation_values), (
        f"QueryType and OperationType share members: "
        f"{query_values & operation_values}"
    )


def test_query_type_is_not_a_subclass_of_operation_type():
    assert not issubclass(QueryType, OperationType)
    assert not issubclass(OperationType, QueryType)


# =============================================
# INVARIANT — ResolvedQuery requires valid QueryType
# =============================================

def test_resolved_query_requires_query_type():
    """Constructing ResolvedQuery without query_type raises TypeError."""
    with pytest.raises(TypeError):
        ResolvedQuery()


def test_resolved_query_accepts_valid_query_type():
    op = ResolvedQuery(query_type=QueryType.QUERY_PRICE, product_id="CQ-44")
    assert op.query_type is QueryType.QUERY_PRICE


# =============================================
# INVARIANT — ResolvedQuery requires product_id (for validity)
# =============================================

def test_resolved_query_with_product_id_is_valid():
    op = ResolvedQuery(query_type=QueryType.QUERY_PRICE, product_id="CQ-44")
    assert op.is_valid() is True


def test_resolved_query_without_product_id_is_invalid():
    op = ResolvedQuery(query_type=QueryType.QUERY_PRICE)
    assert op.is_valid() is False


def test_resolved_query_with_none_product_id_is_invalid():
    op = ResolvedQuery(query_type=QueryType.QUERY_PRICE, product_id=None)
    assert op.is_valid() is False


# =============================================
# INVARIANT — No dependency on command engine / OrderState
# =============================================

def test_resolved_query_module_does_not_import_order_engine(resolved_query_source):
    import_re = re.compile(
        r"^\s*(?:from\s+order\.engine\s+import|import\s+order\.engine)",
        re.MULTILINE,
    )
    assert not import_re.search(resolved_query_source), (
        "resolved_query.py must not import order.engine (T10-P3)."
    )


def test_resolved_query_module_does_not_import_order_state(resolved_query_source):
    import_re = re.compile(
        r"^\s*(?:from\s+order\.state\s+import|import\s+order\.state)",
        re.MULTILINE,
    )
    assert not import_re.search(resolved_query_source), (
        "resolved_query.py must not import order.state (T10-P3)."
    )


# =============================================
# INVARIANT — No modification of EXECUTION_REQUIREMENTS
# =============================================

def test_resolved_query_module_does_not_reference_operation_fields(resolved_query_source):
    assert "EXECUTION_REQUIREMENTS" not in resolved_query_source
    assert "operation_fields" not in resolved_query_source


# =============================================
# evidence default
# =============================================

def test_resolved_query_evidence_defaults_to_empty_list():
    op = ResolvedQuery(query_type=QueryType.QUERY_PRICE, product_id="CQ-44")
    assert op.evidence == []