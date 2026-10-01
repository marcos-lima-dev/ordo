import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from pipeline.telegram_transport import (
    TelegramTransport,
    TransportFailure,
    next_offset,
)


_MODULE_PATH = (
    Path(__file__).parent.parent / "pipeline" / "telegram_transport.py"
)


def _ok_response(updates):
    return json.dumps({"ok": True, "result": updates}).encode()


def _fail_response(reason="bad"):
    return json.dumps({"ok": False, "description": reason}).encode()


def _ok_send_response():
    return json.dumps({"ok": True, "result": {"message_id": 1}}).encode()


# =============================================
# TT-01 — token validation
# =============================================

def test_tt01_empty_token_rejected():
    with pytest.raises(ValueError):
        TelegramTransport("")


def test_tt01b_whitespace_token_rejected():
    with pytest.raises(ValueError):
        TelegramTransport("   ")


# =============================================
# TT-02 — request shape
# =============================================

def test_tt02_url_contains_token_and_endpoint():
    captured = {}

    def fake_http_get(url, timeout):
        captured["url"] = url
        return _ok_response([])

    t = TelegramTransport("SECRET-TOKEN", http_get=fake_http_get)
    t.get_updates(offset=100)

    assert "SECRET-TOKEN" in captured["url"]
    assert "getUpdates" in captured["url"]
    assert "offset=100" in captured["url"]


def test_tt02b_token_not_exposed_as_attribute_by_name():
    """Token is stored; nothing in public surface returns it directly."""
    t = TelegramTransport("SECRET-TOKEN")
    assert not hasattr(t, "token")
    assert not hasattr(t, "get_token")


# =============================================
# TT-03 — response parsing
# =============================================

def test_tt03_valid_response():
    def fake_http_get(url, timeout):
        return _ok_response([{"update_id": 1, "message": {}}])

    t = TelegramTransport("tok", http_get=fake_http_get)
    updates = t.get_updates()
    assert updates == [{"update_id": 1, "message": {}}]


def test_tt03b_empty_updates():
    def fake_http_get(url, timeout):
        return _ok_response([])

    t = TelegramTransport("tok", http_get=fake_http_get)
    assert t.get_updates() == []


# =============================================
# TT-04 — failures
# =============================================

def test_tt04_http_exception_wrapped():
    def fake_http_get(url, timeout):
        raise OSError("network down")

    t = TelegramTransport("tok", http_get=fake_http_get)
    with pytest.raises(TransportFailure):
        t.get_updates()


def test_tt04b_invalid_json_wrapped():
    def fake_http_get(url, timeout):
        return b"not json"

    t = TelegramTransport("tok", http_get=fake_http_get)
    with pytest.raises(TransportFailure):
        t.get_updates()


def test_tt04c_ok_false_wrapped():
    def fake_http_get(url, timeout):
        return _fail_response()

    t = TelegramTransport("tok", http_get=fake_http_get)
    with pytest.raises(TransportFailure):
        t.get_updates()


def test_tt04d_missing_result_wrapped():
    def fake_http_get(url, timeout):
        return json.dumps({"ok": True}).encode()

    t = TelegramTransport("tok", http_get=fake_http_get)
    with pytest.raises(TransportFailure):
        t.get_updates()


# =============================================
# TT-05 — next_offset
# =============================================

def test_tt05_empty_returns_none():
    assert next_offset([]) is None


def test_tt05b_single_returns_plus_one():
    assert next_offset([{"update_id": 41}]) == 42


def test_tt05c_max_plus_one():
    assert next_offset([
        {"update_id": 41}, {"update_id": 43}, {"update_id": 42},
    ]) == 44


def test_tt05d_ignores_non_dict_and_missing_update_id():
    assert next_offset([
        {"update_id": 41}, "garbage", {}, {"update_id": "not int"},
    ]) == 42


# =============================================
# TT-06 — dependency isolation (AST)
# =============================================

_ALLOWED_IMPORTS = {
    "__future__",
    "json",
    "typing",
    "urllib.parse",
    "urllib.request",
}


def test_tt06_imports_only_allowed():
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module in _ALLOWED_IMPORTS, (
                f"unexpected import: {node.module}"
            )
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name in _ALLOWED_IMPORTS, (
                    f"unexpected import: {alias.name}"
                )


def test_tt06b_no_or_do_or_adapter_imports():
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for tok in (
                "order", "application", "conversation", "channel",
                "telegram_adapter", "telegram_shadow",
            ):
                assert tok not in node.module, (
                    f"imports forbidden {tok!r} via {node.module!r}"
                )


# =============================================
# TT-07 — send_message: request shape
# =============================================

def test_tt07_send_message_builds_post_url():
    captured = {}

    def fake_http_post(url, data, timeout):
        captured["url"] = url
        return _ok_send_response()

    t = TelegramTransport("SECRET-TOKEN", http_post=fake_http_post)
    t.send_message("555", "hello")

    assert "SECRET-TOKEN" in captured["url"]
    assert "sendMessage" in captured["url"]


def test_tt07b_send_message_posts_json_body():
    captured = {}

    def fake_http_post(url, data, timeout):
        captured["data"] = data
        return _ok_send_response()

    t = TelegramTransport("tok", http_post=fake_http_post)
    t.send_message("555", "hello")

    body = json.loads(captured["data"].decode("utf-8"))
    assert body == {"chat_id": "555", "text": "hello"}


# =============================================
# TT-08 — send_message: failures
# =============================================

def test_tt08_send_message_http_failure_wrapped():
    def fake_http_post(url, data, timeout):
        raise OSError("network down")

    t = TelegramTransport("tok", http_post=fake_http_post)
    with pytest.raises(TransportFailure):
        t.send_message("555", "hello")


def test_tt08b_send_message_ok_false_wrapped():
    def fake_http_post(url, data, timeout):
        return _fail_response("bad chat")

    t = TelegramTransport("tok", http_post=fake_http_post)
    with pytest.raises(TransportFailure):
        t.send_message("555", "hello")


def test_tt08c_send_message_invalid_json_wrapped():
    def fake_http_post(url, data, timeout):
        return b"not json"

    t = TelegramTransport("tok", http_post=fake_http_post)
    with pytest.raises(TransportFailure):
        t.send_message("555", "hello")


# =============================================
# TT-09 — send_message: input validation
# =============================================

def test_tt09_send_message_rejects_empty_chat_id():
    t = TelegramTransport("tok", http_post=lambda *a, **k: _ok_send_response())
    with pytest.raises(ValueError):
        t.send_message("", "hello")


def test_tt09b_send_message_rejects_whitespace_chat_id():
    t = TelegramTransport("tok", http_post=lambda *a, **k: _ok_send_response())
    with pytest.raises(ValueError):
        t.send_message("   ", "hello")


def test_tt09c_send_message_rejects_empty_text():
    t = TelegramTransport("tok", http_post=lambda *a, **k: _ok_send_response())
    with pytest.raises(ValueError):
        t.send_message("555", "   ")