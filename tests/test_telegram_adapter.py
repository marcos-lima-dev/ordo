import ast
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from pipeline.channel_identity import ChannelIdentity
from pipeline.idempotency import ExternalMessageId
from pipeline.telegram_adapter import (
    ParseStatus,
    ParsedMessage,
    TelegramAdapter,
)


_MODULE_PATH = (
    Path(__file__).parent.parent / "pipeline" / "telegram_adapter.py"
)


ALLOWED = {"12345", "67890"}


def _adapter():
    return TelegramAdapter(allowed_chat_ids=ALLOWED)


def _update(
    chat_id=12345, message_id=42, text="manda o provolone",
    chat_type="private", is_bot=False,
):
    return {
        "update_id": 1,
        "message": {
            "message_id": message_id,
            "from": {"id": 999, "is_bot": is_bot},
            "chat": {"id": chat_id, "type": chat_type},
            "text": text,
        },
    }


# =============================================
# TA-01 — happy path
# =============================================

def test_ta01_private_text_parses():
    result = _adapter().parse(_update())
    assert result.status is ParseStatus.PARSED
    assert isinstance(result.message, ParsedMessage)


def test_ta01b_chat_id_to_channel_identity():
    result = _adapter().parse(_update(chat_id=67890))
    assert result.message.channel_identity == ChannelIdentity(
        channel="telegram", external_conversation_id="67890"
    )


def test_ta01c_message_id_to_external_message_id():
    result = _adapter().parse(_update(message_id=1234))
    assert result.message.external_message_id == ExternalMessageId(value="1234")


def test_ta01d_text_preserved():
    result = _adapter().parse(_update(text="tem brie?"))
    assert result.message.text == "tem brie?"


# =============================================
# TA-02 — ignored
# =============================================

def test_ta02_no_message_ignored():
    result = _adapter().parse({"update_id": 1})
    assert result.status is ParseStatus.IGNORED
    assert result.reason == "no_message"


def test_ta02b_bot_message_ignored():
    result = _adapter().parse(_update(is_bot=True))
    assert result.status is ParseStatus.IGNORED
    assert result.reason == "from_bot"


def test_ta02c_edited_message_ignored():
    result = _adapter().parse({"update_id": 1, "edited_message": {"x": 1}})
    assert result.status is ParseStatus.IGNORED
    assert result.reason == "edited_message"


def test_ta02d_channel_post_ignored():
    result = _adapter().parse({"update_id": 1, "channel_post": {"x": 1}})
    assert result.status is ParseStatus.IGNORED
    assert result.reason == "channel_post"


# =============================================
# TA-03 — rejected
# =============================================

def test_ta03_no_text_rejected():
    u = _update()
    del u["message"]["text"]
    result = _adapter().parse(u)
    assert result.status is ParseStatus.REJECTED
    assert result.reason == "no_text"


def test_ta03b_empty_text_rejected():
    result = _adapter().parse(_update(text="   "))
    assert result.status is ParseStatus.REJECTED
    assert result.reason == "no_text"


def test_ta03c_group_rejected():
    result = _adapter().parse(_update(chat_type="group"))
    assert result.status is ParseStatus.REJECTED
    assert result.reason == "not_private_chat"


def test_ta03d_supergroup_rejected():
    result = _adapter().parse(_update(chat_type="supergroup"))
    assert result.status is ParseStatus.REJECTED


def test_ta03e_channel_rejected():
    result = _adapter().parse(_update(chat_type="channel"))
    assert result.status is ParseStatus.REJECTED


def test_ta03f_chat_not_allowed_rejected():
    result = _adapter().parse(_update(chat_id=99999))
    assert result.status is ParseStatus.REJECTED
    assert result.reason == "chat_not_allowed"


def test_ta03g_malformed_identity_no_chat():
    u = _update()
    del u["message"]["chat"]
    result = _adapter().parse(u)
    assert result.status is ParseStatus.REJECTED
    assert result.reason == "malformed_identity"


def test_ta03h_malformed_identity_no_chat_id():
    u = _update()
    del u["message"]["chat"]["id"]
    result = _adapter().parse(u)
    assert result.status is ParseStatus.REJECTED


def test_ta03i_malformed_identity_no_message_id():
    u = _update()
    del u["message"]["message_id"]
    result = _adapter().parse(u)
    assert result.status is ParseStatus.REJECTED


def test_ta03j_non_dict_rejected():
    result = _adapter().parse("not a dict")  # type: ignore
    assert result.status is ParseStatus.REJECTED


# =============================================
# TA-04 — allowlist
# =============================================

def test_ta04_empty_allowlist_rejects_everything():
    result = TelegramAdapter(allowed_chat_ids=set()).parse(_update())
    assert result.status is ParseStatus.REJECTED
    assert result.reason == "chat_not_allowed"


def test_ta04b_string_and_int_ids_equivalent():
    a = TelegramAdapter(allowed_chat_ids={12345})
    b = TelegramAdapter(allowed_chat_ids={"12345"})
    assert a.parse(_update()).status is ParseStatus.PARSED
    assert b.parse(_update()).status is ParseStatus.PARSED


# =============================================
# TA-05 — ParsedMessage frozen
# =============================================

def test_ta05_parsed_message_frozen():
    m = ParsedMessage(
        channel_identity=ChannelIdentity(channel="telegram", external_conversation_id="1"),
        external_message_id=ExternalMessageId(value="2"),
        text="x",
    )
    with pytest.raises(FrozenInstanceError):
        m.text = "y"


# =============================================
# TA-06 — dependency isolation (AST)
# =============================================

_ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "enum",
    "typing",
    "pipeline.channel_identity",
    "pipeline.idempotency",
}


def test_ta06_imports_only_allowed():
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


def test_ta06b_no_forbidden_modules_by_ast():
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    forbidden = (
        "order", "application_orchestrator", "command_execution",
        "application_caller", "conversation_session",
        "conversation_mapping", "telegram_transport",
        "telegram_shadow", "application_processing",
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for tok in forbidden:
                assert tok not in node.module, (
                    f"imports forbidden {tok!r} via {node.module!r}"
                )


# =============================================
# TA-07 — privacy
# =============================================

def test_ta07_no_profile_fields_read():
    """AST: adapter does not access username, first_name, last_name, etc."""
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    forbidden_attrs = {
        "username", "first_name", "last_name", "language_code",
        "is_premium", "photo", "bio", "description", "title",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr not in forbidden_attrs, (
                f"reads forbidden profile field {node.attr!r}"
            )
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            for name in forbidden_attrs:
                assert f'"{name}"' not in node.value, (
                    f"string references profile field {name!r}"
                )
                assert f"'{name}'" not in node.value, (
                    f"string references profile field {name!r}"
                )