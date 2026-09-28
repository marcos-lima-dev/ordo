import ast
import sys
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from pipeline.channel_identity import ChannelIdentity


_MODULE_PATH = (
    Path(__file__).parent.parent / "pipeline" / "channel_identity.py"
)


# =============================================
# CI-01 — structure
# =============================================

def test_ci01_fields_exact():
    assert {f.name for f in fields(ChannelIdentity)} == {
        "channel", "external_conversation_id",
    }


def test_ci01b_frozen():
    ci = ChannelIdentity(channel="telegram", external_conversation_id="123")
    with pytest.raises(FrozenInstanceError):
        ci.channel = "whatsapp"


def test_ci01c_hashable_and_eq():
    a = ChannelIdentity(channel="telegram", external_conversation_id="123")
    b = ChannelIdentity(channel="telegram", external_conversation_id="123")
    c = ChannelIdentity(channel="whatsapp", external_conversation_id="123")
    assert a == b
    assert a != c
    assert {a, b, c} == {a, c}


def test_ci01d_no_message_identity_field():
    """P78: ChannelIdentity must not carry message identity."""
    field_names = {f.name for f in fields(ChannelIdentity)}
    for forbidden in (
        "external_message_id", "message_id", "update_id",
    ):
        assert forbidden not in field_names


# =============================================
# CI-02 — validation
# =============================================

@pytest.mark.parametrize("value", ["", "   ", "\t", "\n"])
def test_ci02_empty_channel_rejected(value):
    with pytest.raises(ValueError):
        ChannelIdentity(channel=value, external_conversation_id="123")


@pytest.mark.parametrize("value", ["", "   ", "\t", "\n"])
def test_ci02b_empty_external_conversation_id_rejected(value):
    with pytest.raises(ValueError):
        ChannelIdentity(channel="telegram", external_conversation_id=value)


def test_ci02c_non_str_channel_rejected():
    with pytest.raises(ValueError):
        ChannelIdentity(channel=123, external_conversation_id="123")  # type: ignore


def test_ci02d_non_str_external_id_rejected():
    with pytest.raises(ValueError):
        ChannelIdentity(channel="telegram", external_conversation_id=123)  # type: ignore


# =============================================
# CI-03 — channel is not a closed enum
# =============================================

@pytest.mark.parametrize("channel", ["telegram", "whatsapp", "web", "discord", "email"])
def test_ci03_open_channel_namespace(channel):
    ci = ChannelIdentity(channel=channel, external_conversation_id="x")
    assert ci.channel == channel


# =============================================
# CI-04 — dependency isolation
# =============================================

def test_ci04_imports_only_allowed():
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    allowed = {"__future__", "dataclasses"}
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


def test_ci04b_no_provider_tokens_in_code():
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

    forbidden = ("chat_id", "phone", "update_id", "bot_token")
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstring_ids
        ):
            for token in forbidden:
                assert token not in node.value, (
                    f"non-docstring string references {token!r}"
                )