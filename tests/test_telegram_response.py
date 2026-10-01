"""
Tests for Telegram response composition.
"""
import inspect
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

import pipeline.telegram_response as telegram_response_mod
from pipeline.telegram_response import (
    CommunicableResponse,
    compose_response,
)


_MODULE_PATH = (
    Path(__file__).parent.parent / "pipeline" / "telegram_response.py"
)


# ============================================
# Representation
# ============================================

def test_response_is_frozen():
    r = CommunicableResponse(destination="555", text="oi")
    with pytest.raises(FrozenInstanceError):
        r.destination = "666"


# ============================================
# Composer — outcome mapping
# ============================================

@pytest.mark.parametrize("outcome_name", [
    "EXECUTED",
    "CLARIFICATION",
    "SAFETY_BLOCKED",
    "EXECUTION_DISABLED",
    "DUPLICATE",
    "ERROR",
])
def test_composer_returns_response_for_known_outcomes(outcome_name):
    r = compose_response(outcome_name, destination="555")
    assert isinstance(r, CommunicableResponse)
    assert r.destination == "555"
    assert isinstance(r.text, str) and r.text.strip() != ""


def test_composer_returns_none_for_not_eligible():
    assert compose_response("NOT_ELIGIBLE", destination="555") is None


def test_composer_returns_none_for_unknown_outcome():
    assert compose_response("SOMETHING_ELSE", destination="555") is None


def test_composer_returns_none_when_destination_missing():
    assert compose_response("EXECUTED", destination=None) is None


# ============================================
# Isolation — no domain, no Telegram
# ============================================

def test_composer_module_does_not_reference_domain_or_telegram():
    source = inspect.getsource(telegram_response_mod)
    forbidden = [
        "orchestrate_command",
        "OrderEngine",
        "OrderState",
        "ResolutionResult",
        "ExecutionOutcome",
        "TelegramTransport",
        "TelegramControlledExecution",
        "CatalogRetriever",
        "ProductResolver",
        "urlopen",
        "requests",
        "httpx",
    ]
    for tok in forbidden:
        assert tok not in source, f"composer must not reference {tok}"