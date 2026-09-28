"""
Recognition Robustness Stage 1 — corpus regression tests.

Reads the frozen corpus from tests/fixtures/recognition_robustness_corpus.json
and verifies CommandRecognizer and QueryIntentBootstrap behavior.

The corpus was frozen BEFORE implementation (see file notes). Expected
outcomes were declared from design intent, not from mechanism output.

Sections:
    command_must_fire          — the new classes must fire
    command_regression         — existing classes preserved
    command_must_not_fire      — negatives that must NOT fire
    command_characterized_fp   — accepted FPs (mechanism fires; downstream handles)
    query_must_fire            — the new PRICE class must fire
    query_regression           — existing QUERY behavior preserved
    query_characterized_fp     — accepted FPs in QUERY
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from pipeline.command_recognizer import (
    CommandLabel,
    CommandRecognizer,
    RecognitionOutcome,
)
from pipeline.query_intent_bootstrap import QueryIntentBootstrap
from pipeline.query_intent_provider import QueryIntentSignal


_CORPUS_PATH = (
    Path(__file__).parent / "fixtures" / "recognition_robustness_corpus.json"
)

_CORPUS = json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))


_COMMAND_ENTRIES = (
    _CORPUS["command_must_fire"]
    + _CORPUS["command_regression"]
    + _CORPUS["command_must_not_fire"]
    + _CORPUS["command_characterized_fp"]
)

_QUERY_ENTRIES = (
    _CORPUS["query_must_fire"]
    + _CORPUS["query_regression"]
    + _CORPUS["query_characterized_fp"]
)


def _expected_command(expected: str):
    if expected == "UNRECOGNIZED":
        return None
    if expected.startswith("RECOGNIZED:"):
        return CommandLabel[expected.split(":", 1)[1]]
    raise AssertionError(f"unexpected command expectation: {expected!r}")


def _check_command(input_text: str, expected: str) -> None:
    rec = CommandRecognizer()
    result = rec.recognize(input_text)
    if expected == "UNRECOGNIZED":
        assert result.outcome is RecognitionOutcome.UNRECOGNIZED, (
            f"input={input_text!r}: expected UNRECOGNIZED, got {result}"
        )
        assert result.label is None
        return
    want = _expected_command(expected)
    assert result.outcome is RecognitionOutcome.RECOGNIZED, (
        f"input={input_text!r}: expected RECOGNIZED {want.name}, got {result}"
    )
    assert result.label is want, (
        f"input={input_text!r}: expected {want.name}, got {result.label}"
    )


def _check_query(input_text: str, expected: str) -> None:
    bootstrap = QueryIntentBootstrap()
    signal = bootstrap.predict(input_text)
    want = QueryIntentSignal[expected]
    assert signal is want, (
        f"input={input_text!r}: expected {want.name}, got {signal.name}"
    )


# =============================================
# Command corpus
# =============================================

@pytest.mark.parametrize(
    "entry", _COMMAND_ENTRIES, ids=lambda e: e["input"],
)
def test_command_corpus(entry):
    _check_command(entry["input"], entry["expected"])


# =============================================
# Query corpus
# =============================================

@pytest.mark.parametrize(
    "entry", _QUERY_ENTRIES, ids=lambda e: e["input"],
)
def test_query_corpus(entry):
    _check_query(entry["input"], entry["expected"])


# =============================================
# Sanity: corpus has the expected shape
# =============================================

def test_corpus_frozen_before_implementation():
    assert _CORPUS.get("frozen_before_implementation") is True


def test_corpus_checkpoint_matches_expected():
    assert _CORPUS["checkpoint"] == (
        "6361a61aa6ca76c00439d5cbb088b8c92dfce621"
    )


def test_characterized_fp_sections_documented():
    """Accepted FPs must carry a note explaining downstream behavior."""
    for entry in _CORPUS["command_characterized_fp"]:
        assert "note" in entry
        assert "FP" in entry["note"]
    for entry in _CORPUS["query_characterized_fp"]:
        assert "note" in entry
        assert "FP" in entry["note"]