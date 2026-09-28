import ast
import sys
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from pipeline.application_processing import ApplicationProcessor
from pipeline.command_evidence_provider import CommandEvidenceProvider
from pipeline.conversation_mapping import InMemoryConversationMappingStore
from pipeline.query_intent_provider import (
    QueryIntentProvider,
    QueryIntentSignal,
)
from pipeline.signal_observation import CommandEvidence
from pipeline.telegram_adapter import TelegramAdapter
from pipeline.telegram_shadow import (
    ObservationRecord,
    process_update,
    run_shadow_cycle,
)
from pipeline.telegram_transport import TelegramTransport


_MODULE_PATH = (
    Path(__file__).parent.parent / "pipeline" / "telegram_shadow.py"
)


class _Q(QueryIntentProvider):
    def predict(self, message):
        return QueryIntentSignal.UNRESOLVED


class _C(CommandEvidenceProvider):
    def predict(self, message):
        return CommandEvidence.PRESENT


def _processor():
    return ApplicationProcessor(_Q(), _C())


def _update(chat_id=12345, message_id=42, text="manda o provolone"):
    return {
        "update_id": 1,
        "message": {
            "message_id": message_id,
            "from": {"id": 999, "is_bot": False},
            "chat": {"id": chat_id, "type": "private"},
            "text": text,
        },
    }


def _adapter():
    return TelegramAdapter(allowed_chat_ids={12345})


# =============================================
# TS-01 — process_update
# =============================================

def test_ts01_process_update_produces_record():
    record = process_update(
        _update(), _adapter(),
        InMemoryConversationMappingStore(), _processor(),
    )
    assert isinstance(record, ObservationRecord)
    assert record.external_message_id == "42"
    assert record.text == "manda o provolone"
    assert record.observation is not None
    assert record.dispatch_plan is not None


def test_ts01b_ignored_update_returns_none():
    record = process_update(
        {"update_id": 1}, _adapter(),
        InMemoryConversationMappingStore(), _processor(),
    )
    assert record is None


def test_ts01c_rejected_update_returns_none():
    record = process_update(
        _update(chat_id=99999), _adapter(),
        InMemoryConversationMappingStore(), _processor(),
    )
    assert record is None


def test_ts01d_same_chat_same_conversation_id():
    mapping = InMemoryConversationMappingStore()
    r1 = process_update(
        _update(message_id=1), _adapter(), mapping, _processor(),
    )
    r2 = process_update(
        _update(message_id=2), _adapter(), mapping, _processor(),
    )
    assert r1.conversation_id == r2.conversation_id


def test_ts01e_different_chats_different_conversation_ids():
    mapping = InMemoryConversationMappingStore()
    a = process_update(
        _update(chat_id=12345), _adapter(), mapping, _processor(),
    )
    adapter2 = TelegramAdapter(allowed_chat_ids={67890})
    b = process_update(
        _update(chat_id=67890), adapter2, mapping, _processor(),
    )
    assert a.conversation_id != b.conversation_id


# =============================================
# TS-02 — run_shadow_cycle
# =============================================

def test_ts02_cycle_processes_batch():
    def fake_http(url, timeout):
        import json
        return json.dumps({"ok": True, "result": [
            _update(message_id=1, text="manda o provolone"),
            _update(message_id=2, text="tem brie?"),
        ]}).encode()

    transport = TelegramTransport("tok", http_get=fake_http)
    records, offset = run_shadow_cycle(
        transport, _adapter(),
        InMemoryConversationMappingStore(), _processor(),
    )
    assert len(records) == 2
    assert offset == 2


def test_ts02b_offset_passed_through():
    captured = {}

    def fake_http(url, timeout):
        import json
        captured["url"] = url
        return json.dumps({"ok": True, "result": []}).encode()

    transport = TelegramTransport("tok", http_get=fake_http)
    run_shadow_cycle(
        transport, _adapter(),
        InMemoryConversationMappingStore(), _processor(),
        offset=99,
    )
    assert "offset=99" in captured["url"]


# =============================================
# TS-03 — record shape
# =============================================

def test_ts03_record_frozen():
    record = process_update(
        _update(), _adapter(),
        InMemoryConversationMappingStore(), _processor(),
    )
    with pytest.raises(FrozenInstanceError):
        record.text = "x"


def test_ts03b_record_has_only_expected_fields():
    names = {f.name for f in fields(ObservationRecord)}
    assert names == {
        "conversation_id", "external_message_id", "text",
        "observation", "dispatch_plan", "observed_at",
    }


# =============================================
# TS-04 — structural safety (AST)
# =============================================

_FORBIDDEN_MODULES = (
    "application_orchestrator",
    "command_execution",
    "application_caller",
    "order.engine",
    "order.execution",
)


def test_ts04_no_execution_imports():
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for tok in _FORBIDDEN_MODULES:
                assert tok not in node.module, (
                    f"imports forbidden {tok!r} via {node.module!r}"
                )
        if isinstance(node, ast.Import):
            for alias in node.names:
                for tok in _FORBIDDEN_MODULES:
                    assert tok not in alias.name


def test_ts04b_no_session_store_symbol_imported():
    """
    P87: shadow may keep identity state (ConversationId) but must NOT
    import the commercial session store (InMemoryConversationSessionStore
    or ConversationSessionStore).
    """
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    forbidden_symbols = (
        "InMemoryConversationSessionStore",
        "ConversationSessionStore",
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                for tok in forbidden_symbols:
                    assert alias.name != tok, (
                        f"shadow imports forbidden symbol {tok!r}"
                    )
        if isinstance(node, ast.Import):
            for alias in node.names:
                for tok in forbidden_symbols:
                    assert tok not in alias.name


def test_ts04c_no_idempotency_store_symbol_imported():
    """
    P88: shadow must NOT import the idempotency store.
    """
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    forbidden_symbols = (
        "InMemoryIdempotencyStore",
        "IdempotencyStore",
        "IdempotencyKey",
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                for tok in forbidden_symbols:
                    assert alias.name != tok, (
                        f"shadow imports forbidden symbol {tok!r}"
                    )
        if isinstance(node, ast.Import):
            for alias in node.names:
                for tok in forbidden_symbols:
                    assert tok not in alias.name


def test_ts04d_no_engine_orchestrator_symbols_in_code():
    source = _MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    docstring_ids = set()
    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                docstring_ids.add(id(node.body[0].value))
    forbidden = (
        "orchestrate_command",
        "OrderEngine",
        "OrderState",
        "InMemoryIdempotencyStore",
        "InMemoryConversationSessionStore",
        "execute_resolution",
        "compose_command_execution",
    )
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstring_ids
        ):
            for tok in forbidden:
                assert tok not in node.value, (
                    f"non-docstring references {tok!r}"
                )


def test_ts04e_no_direct_engine_apply_call():
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "apply":
            raise AssertionError(
                f"direct .apply() call at line {node.lineno}"
            )


# =============================================
# TS-05 — token never in records
# =============================================

def test_ts05_token_not_in_record():
    token = "SUPER-SECRET-TOKEN"

    def fake_http(url, timeout):
        import json
        return json.dumps({"ok": True, "result": [_update()]}).encode()

    transport = TelegramTransport(token, http_get=fake_http)
    records, _ = run_shadow_cycle(
        transport, _adapter(),
        InMemoryConversationMappingStore(), _processor(),
    )
    for r in records:
        assert token not in r.text
        assert token not in r.external_message_id
        assert token not in r.conversation_id.value