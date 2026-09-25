"""
ORDO — Recognizer-backed CommandEvidenceProvider (Track 10, Stage 4I.4c).

Concrete CommandEvidenceProvider that delegates COMMAND recognition
to an injected CommandRecognizer and maps its outcome to
CommandEvidence.

Scope:
    - Wraps exactly one CommandRecognizer.
    - Produces CommandEvidence from a message.
    - Does NOT recognize by itself.
    - Does NOT resolve operations.
    - Does NOT touch OrderState, OrderEngine, or any pipeline.

Frozen mapping:
    RecognitionOutcome.RECOGNIZED   -> CommandEvidence.PRESENT
    RecognitionOutcome.UNRECOGNIZED -> CommandEvidence.INDETERMINATE
    Recognizer exception            -> propagate (never captured)

ABSENT is not producible by this provider (V1).
T10-P28: the recognizer produces no positive negative evidence, so
this provider has no honest path to emit ABSENT.

Principles honored:
    T10-P26  COMMAND EVIDENCE != COMMAND INTENT
    T10-P27  UNKNOWN recognition != ABSENT
    T10-P28  ABSENT requires positive negative evidence
    T10-P31  UNKNOWN classification != unexpected value
    T10-P32  EvidenceProvider != Recognizer Owner
    T10-P37  UNSUPPORTED EVIDENCE != FORBIDDEN SYMBOL

This module does NOT:
    - interpret natural language;
    - access result.label;
    - import CommandLabel;
    - import any benchmark, adapter, ML, or resolution module;
    - carry dispatch, routing, or execution semantics;
    - contain try/except around the recognizer call.
"""
from __future__ import annotations

from pipeline.command_evidence_provider import CommandEvidenceProvider
from pipeline.command_recognizer import CommandRecognizer, RecognitionOutcome
from pipeline.signal_observation import CommandEvidence


class RecognizerCommandEvidenceProvider(CommandEvidenceProvider):
    """
    CommandEvidenceProvider that observes an injected CommandRecognizer.

    The recognizer is mandatory. This provider is not the owner of
    the recognition strategy (T10-P32).
    """

    def __init__(self, recognizer: CommandRecognizer) -> None:
        self._recognizer = recognizer

    def predict(self, message: str) -> CommandEvidence:
        """
        Map the recognizer outcome to CommandEvidence.

        RecognitionOutcome.RECOGNIZED   -> CommandEvidence.PRESENT
        RecognitionOutcome.UNRECOGNIZED -> CommandEvidence.INDETERMINATE

        Any exception raised by the recognizer propagates unchanged.
        This provider never captures or converts exceptions into
        evidence (T10-P31 / T10-P35).
        """
        result = self._recognizer.recognize(message)

        if result.outcome is RecognitionOutcome.RECOGNIZED:
            return CommandEvidence.PRESENT
        if result.outcome is RecognitionOutcome.UNRECOGNIZED:
            return CommandEvidence.INDETERMINATE

        # Unreachable per the recognizer contract (T10-P35: no INVALID).
        raise AssertionError(
            f"unrecognized RecognitionOutcome: {result.outcome!r}"
        )