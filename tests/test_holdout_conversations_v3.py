import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import re
import pytest

V3_PATH = Path(__file__).parent.parent / "scripts" / "run_holdout_conversations_v3.py"


@pytest.fixture(scope="module")
def v3_source():
    return V3_PATH.read_text(encoding="utf-8")


def test_v3_1_uses_pipeline_resolve_operation(v3_source):
    """V3-1: runner obtains ResolutionResult from the canonical pipeline."""
    assert "from pipeline.resolution_pipeline import" in v3_source
    assert re.search(r"\bresolve_operation\s*\(", v3_source)


def test_v3_2_uses_execution_caller(v3_source):
    """V3-2: execution passes through execute_resolution."""
    assert "from order.execution import" in v3_source
    assert re.search(r"\bexecute_resolution\s*\(", v3_source)


def test_v3_3_no_resolved_operation_constructor(v3_source):
    """V3-3: runner must not construct ResolvedOperation directly."""
    assert "ResolvedOperation(" not in v3_source


def test_v3_4_no_parallel_product_selection(v3_source):
    """V3-4: runner must not select product_id from candidates."""
    assert "candidates[0]" not in v3_source
    assert not re.search(r"product_id\s*=\s*candidates", v3_source)


def test_v3_5_no_parallel_target_selection(v3_source):
    """V3-5: runner must not select target_item_id semantically."""
    assert not re.search(r"target_id\s*=\s*item\.id", v3_source)
    assert not re.search(r"target_item_id\s*=\s*item\.id", v3_source)


def test_v3_6_no_unknown_fallback_operation(v3_source):
    """V3-6: runner must not fabricate UNKNOWN ResolvedOperation fallback."""
    assert "ResolvedOperation(type=OperationType.UNKNOWN)" not in v3_source
    assert "OperationType.UNKNOWN" not in v3_source


def test_v3_7_no_fabricated_metadata(v3_source):
    """V3-7: runner must not inject source_message_id or evidence."""
    assert not re.search(r"source_message_id\s*=", v3_source)
    assert not re.search(r"evidence\s*=\s*\[", v3_source)