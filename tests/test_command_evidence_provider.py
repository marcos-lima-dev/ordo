import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from pipeline.command_evidence_provider import CommandEvidenceProvider
from pipeline.signal_observation import CommandEvidence


# =============================================
# CEP-01 — abstract contract
# =============================================

def test_cep01_provider_is_abstract():
    with pytest.raises(TypeError):
        CommandEvidenceProvider()


def test_cep01b_incomplete_subclass_raises():
    class Incomplete(CommandEvidenceProvider):
        pass

    with pytest.raises(TypeError):
        Incomplete()


def test_cep01c_predict_is_abstract():
    assert "predict" in CommandEvidenceProvider.__abstractmethods__


# =============================================
# CEP-02 — minimal implementations
# =============================================

def test_cep02_minimal_present():
    class AlwaysPresent(CommandEvidenceProvider):
        def predict(self, message: str) -> CommandEvidence:
            return CommandEvidence.PRESENT

    assert AlwaysPresent().predict("x") is CommandEvidence.PRESENT


def test_cep02b_minimal_absent():
    class AlwaysAbsent(CommandEvidenceProvider):
        def predict(self, message: str) -> CommandEvidence:
            return CommandEvidence.ABSENT

    assert AlwaysAbsent().predict("x") is CommandEvidence.ABSENT


def test_cep02c_minimal_indeterminate():
    class AlwaysIndeterminate(CommandEvidenceProvider):
        def predict(self, message: str) -> CommandEvidence:
            return CommandEvidence.INDETERMINATE

    assert AlwaysIndeterminate().predict("x") is CommandEvidence.INDETERMINATE


def test_cep02d_substitutable():
    """Two implementations can sit behind the same contract."""

    class P(CommandEvidenceProvider):
        def predict(self, message: str) -> CommandEvidence:
            return CommandEvidence.PRESENT

    class I(CommandEvidenceProvider):
        def predict(self, message: str) -> CommandEvidence:
            return CommandEvidence.INDETERMINATE

    providers = [P(), I()]
    assert [p.predict("x") for p in providers] == [
        CommandEvidence.PRESENT,
        CommandEvidence.INDETERMINATE,
    ]


# =============================================
# CEP-03 — operational failure is an exception
# =============================================

def test_cep03_failure_propagates_as_exception():
    class Broken(CommandEvidenceProvider):
        def predict(self, message: str) -> CommandEvidence:
            raise RuntimeError("model unavailable")

    with pytest.raises(RuntimeError, match="model unavailable"):
        Broken().predict("x")


def test_cep03b_failure_does_not_return_evidence():
    class Broken(CommandEvidenceProvider):
        def predict(self, message: str) -> CommandEvidence:
            raise RuntimeError("failure")

    p = Broken()
    try:
        result = p.predict("x")
    except RuntimeError:
        return
    assert result not in CommandEvidence, (
        "provider returned an evidence value during operational failure"
    )


# =============================================
# CEP-04 — exact CommandEvidence type
# =============================================

def test_cep04_uses_stage_4i1_command_evidence():
    """
    The contract must use the exact CommandEvidence from Stage 4I.1.
    No local redefinition.
    """
    import pipeline.signal_observation as so
    import pipeline.command_evidence_provider as cep
    assert cep.CommandEvidence is so.CommandEvidence


def test_cep04b_no_new_command_enum_defined():
    source = (
        Path(__file__).parent.parent
        / "pipeline"
        / "command_evidence_provider.py"
    ).read_text(encoding="utf-8")
    assert "class CommandEvidence(" not in source, (
        "command_evidence_provider.py must not redefine CommandEvidence"
    )


# =============================================
# CEP-05 — dependency boundaries
# =============================================

def test_cep05_no_forbidden_imports():
    """
    Non-docstring string constants must not reference forbidden
    modules or symbols. Docstrings are excluded: the prohibition
    targets signals, not documentation prose.
    """
    import ast

    source = (
        Path(__file__).parent.parent
        / "pipeline"
        / "command_evidence_provider.py"
    ).read_text(encoding="utf-8")

    tree = ast.parse(source)

    docstring_value_ids = set()
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
                docstring_value_ids.add(id(node.body[0].value))

    forbidden = (
        "benchmark",
        "ModularAdapter",
        "semantic_intent_router",
        "SemanticIntent",
        "OperationType",
        "QueryType",
        "QueryIntentProvider",
        "QueryIntentBootstrap",
        "order.state",
        "order.engine",
        "OrderState",
        "OrderEngine",
        "ResolutionResult",
        "QueryResolutionResult",
        "operation_resolver",
        "catalog_retriever",
        "product_resolver",
        "resolve_operation",
        "resolve_query",
    )

    # Check only non-docstring string constants.
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstring_value_ids
        ):
            for token in forbidden:
                assert token not in node.value, (
                    f"non-docstring string references {token!r}: "
                    f"{node.value!r}"
                )

    # Also ensure none of the forbidden modules appear as imports.
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for token in forbidden:
                assert token not in node.module, (
                    f"module imports forbidden {token!r}"
                )
        if isinstance(node, ast.Import):
            for alias in node.names:
                for token in forbidden:
                    assert token not in alias.name, (
                        f"module imports forbidden {token!r}"
                    )


def test_cep05b_imports_command_evidence_from_stage_4i1():
    source = (
        Path(__file__).parent.parent
        / "pipeline"
        / "command_evidence_provider.py"
    ).read_text(encoding="utf-8")
    assert "from pipeline.signal_observation import CommandEvidence" in source


# =============================================
# CEP-06 — no dispatch/resolution/execution authority
# =============================================

def test_cep06_provider_surface_is_minimal():
    public = [
        name
        for name in dir(CommandEvidenceProvider)
        if not name.startswith("_")
    ]
    assert set(public) == {"predict"}


def test_cep06b_no_resolution_or_dispatch_methods():
    forbidden_names = (
        "dispatch",
        "route",
        "plan",
        "authorize",
        "execute",
        "apply",
        "resolve",
    )
    for name in forbidden_names:
        assert not hasattr(CommandEvidenceProvider, name), (
            f"CommandEvidenceProvider must not expose {name!r}"
        )


# =============================================
# CEP-07 — no recognition logic in production module
# =============================================

def test_cep07_no_regex_or_string_mapping():
    """
    The production module must not contain regex imports or COMMAND
    string labels as code (non-docstring). Docstrings may reference
    these tokens for documentation purposes.
    """
    import ast

    source = (
        Path(__file__).parent.parent
        / "pipeline"
        / "command_evidence_provider.py"
    ).read_text(encoding="utf-8")

    tree = ast.parse(source)

    docstring_value_ids = set()
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
                docstring_value_ids.add(id(node.body[0].value))

    # No `import re` anywhere.
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "re", (
                    "command_evidence_provider.py must not import re"
                )

    # No COMMAND string labels in non-docstring string constants.
    forbidden_tokens = (
        "ADD_ITEM",
        "REMOVE_ITEM",
        "CHANGE_QUANTITY",
        "REPLACE_ITEM",
        "CONFIRM_ORDER",
        "CANCEL_ORDER",
        "UNKNOWN",
    )
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstring_value_ids
        ):
            for token in forbidden_tokens:
                assert token not in node.value, (
                    f"non-docstring string contains {token!r}: "
                    f"{node.value!r}"
                )