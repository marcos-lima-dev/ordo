import ast
import threading
import sys
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from pipeline.conversation_session import ConversationId
from pipeline.idempotency import (
    ClaimRecord,
    ClaimStatus,
    ExternalMessageId,
    IdempotencyKey,
    InMemoryIdempotencyStore,
)


_MODULE_PATH = (
    Path(__file__).parent.parent / "pipeline" / "idempotency.py"
)


def _cid(v: str) -> ConversationId:
    return ConversationId(value=v)


def _emid(v: str) -> ExternalMessageId:
    return ExternalMessageId(value=v)


def _key(c: str, m: str) -> IdempotencyKey:
    return IdempotencyKey(_cid(c), _emid(m))


# =============================================
# ID-01 — types
# =============================================

def test_id01_external_message_id_has_only_value():
    assert {f.name for f in fields(ExternalMessageId)} == {"value"}


def test_id01b_external_message_id_frozen():
    x = _emid("42")
    with pytest.raises(FrozenInstanceError):
        x.value = "43"


def test_id02_idempotency_key_fields():
    assert {f.name for f in fields(IdempotencyKey)} == {
        "conversation_id", "external_message_id",
    }


def test_id02b_idempotency_key_frozen():
    k = _key("A", "42")
    with pytest.raises(FrozenInstanceError):
        k.external_message_id = _emid("43")


def test_id02c_idempotency_key_hashable():
    k1 = _key("A", "42")
    k2 = _key("A", "42")
    k3 = _key("A", "43")
    assert hash(k1) == hash(k2)
    assert k1 != k3
    assert {k1, k2, k3} == {k1, k3}


def test_id03_claim_record_fields():
    assert {f.name for f in fields(ClaimRecord)} == {
        "key", "claimed", "completed",
    }


def test_id03b_claim_status_enum():
    assert {s.name for s in ClaimStatus} == {
        "CLAIMED", "ALREADY_CLAIMED",
    }


# =============================================
# ID-04 — claim semantics
# =============================================

def test_id04_first_claim_wins():
    store = InMemoryIdempotencyStore()
    k = _key("A", "42")
    assert store.claim(k) is ClaimStatus.CLAIMED


def test_id04b_second_claim_loses():
    store = InMemoryIdempotencyStore()
    k = _key("A", "42")
    store.claim(k)
    assert store.claim(k) is ClaimStatus.ALREADY_CLAIMED


def test_id04c_claim_after_complete_still_loses():
    store = InMemoryIdempotencyStore()
    k = _key("A", "42")
    store.claim(k)
    store.complete(k)
    assert store.claim(k) is ClaimStatus.ALREADY_CLAIMED


# =============================================
# ID-05 — complete semantics
# =============================================

def test_id05_complete_marks_record():
    store = InMemoryIdempotencyStore()
    k = _key("A", "42")
    store.claim(k)
    store.complete(k)
    rec = store.get(k)
    assert rec is not None
    assert rec.claimed is True
    assert rec.completed is True


def test_id05b_complete_without_claim_raises():
    store = InMemoryIdempotencyStore()
    k = _key("A", "42")
    with pytest.raises(KeyError):
        store.complete(k)


def test_id05c_complete_twice_is_noop():
    store = InMemoryIdempotencyStore()
    k = _key("A", "42")
    store.claim(k)
    store.complete(k)
    store.complete(k)
    assert store.get(k).completed is True


# =============================================
# ID-06 — get semantics
# =============================================

def test_id06_get_unknown_returns_none():
    store = InMemoryIdempotencyStore()
    assert store.get(_key("A", "42")) is None


def test_id06b_get_after_claim_before_complete():
    store = InMemoryIdempotencyStore()
    k = _key("A", "42")
    store.claim(k)
    rec = store.get(k)
    assert rec.claimed is True
    assert rec.completed is False


# =============================================
# ID-07 — key isolation
# =============================================

def test_id07_same_message_id_different_conversation_isolated():
    store = InMemoryIdempotencyStore()
    k_a = _key("A", "42")
    k_b = _key("B", "42")
    assert store.claim(k_a) is ClaimStatus.CLAIMED
    assert store.claim(k_b) is ClaimStatus.CLAIMED


def test_id07b_same_conversation_different_message_id_isolated():
    store = InMemoryIdempotencyStore()
    assert store.claim(_key("A", "42")) is ClaimStatus.CLAIMED
    assert store.claim(_key("A", "43")) is ClaimStatus.CLAIMED


# =============================================
# ID-08 — concurrent claim (atomicity)
# =============================================

def test_id08_concurrent_claim_exactly_one_wins():
    store = InMemoryIdempotencyStore()
    key = _key("A", "42")
    results = []
    barrier = threading.Barrier(10)

    def worker():
        barrier.wait()
        results.append(store.claim(key))

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 10
    assert results.count(ClaimStatus.CLAIMED) == 1
    assert results.count(ClaimStatus.ALREADY_CLAIMED) == 9


def test_id08b_concurrent_claim_across_keys():
    store = InMemoryIdempotencyStore()
    keys = [_key("A", str(i)) for i in range(5)]
    results = []
    barrier = threading.Barrier(5)

    def worker(k):
        barrier.wait()
        results.append(store.claim(k))

    threads = [threading.Thread(target=worker, args=(k,)) for k in keys]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results.count(ClaimStatus.CLAIMED) == 5


# =============================================
# ID-09 — dependency isolation
# =============================================

def test_id09_imports_only_allowed():
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    allowed = {
        "__future__",
        "dataclasses",
        "enum",
        "threading",
        "typing",
        "pipeline.conversation_session",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module in allowed, (
                f"unexpected import: {node.module}"
            )
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name in allowed, (
                    f"unexpected import: {alias.name}"
                )