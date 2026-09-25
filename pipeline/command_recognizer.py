"""
ORDO — Command Recognizer (Track 10, Stage 4I.4b).

Fresh, deterministic COMMAND recognizer, characterized against the
legacy behavior frozen in Stage 4I.4a.

Scope:
    - Recognizes COMMAND labels only.
    - Does NOT emit CommandEvidence (T10-P32).
    - Does NOT resolve operations. Does NOT touch OrderState.
    - Does NOT know QUERY, SemanticIntent, or OperationType.

Domain (v1): the five historically recognized COMMAND labels:
    ADD_ITEM
    REMOVE_ITEM
    CHANGE_QUANTITY
    CONFIRM_ORDER
    CANCEL_ORDER

REPLACE_ITEM is intentionally absent (registered GAP from 4I.4).

Outcomes (T10-P35):
    RECOGNIZED
    UNRECOGNIZED

Unexpected classifier output is NOT a semantic outcome. It raises.

Legacy equivalence (T10-P36):
    For valid inputs, behavior mirrors the historical recognizer.
    One deliberate divergence is authorized and required:
        legacy: unexpected classifier label -> "UNKNOWN"
        new:    unexpected classifier label -> exception

No heavy dependencies. No model loading. Optional classifier is
injected as a lightweight callable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Mapping, Optional, Union


class CommandLabel(Enum):
    """
    Closed-set COMMAND labels recognized by v1.

    REPLACE_ITEM and QUERY labels are deliberately absent.
    """
    ADD_ITEM = "ADD_ITEM"
    REMOVE_ITEM = "REMOVE_ITEM"
    CHANGE_QUANTITY = "CHANGE_QUANTITY"
    CONFIRM_ORDER = "CONFIRM_ORDER"
    CANCEL_ORDER = "CANCEL_ORDER"


class RecognitionOutcome(Enum):
    """
    Semantic outcomes of the recognizer.

    INVALID is deliberately NOT a value (T10-P35).
    """
    RECOGNIZED = "RECOGNIZED"
    UNRECOGNIZED = "UNRECOGNIZED"


@dataclass(frozen=True)
class RecognitionResult:
    """
    Result of recognition.

    If outcome is RECOGNIZED, label is a CommandLabel.
    If outcome is UNRECOGNIZED, label is None.
    """
    outcome: RecognitionOutcome
    label: Optional[CommandLabel] = None


class UnexpectedClassifierOutput(Exception):
    """
    Raised when the injected classifier returns a label outside the
    provided label_map (T10-P31 / T10-P34 / T10-P35).

    This is not an operational failure of the classifier; it is a
    contract violation at the first boundary capable of detecting it.
    """
    def __init__(self, raw_label):
        self.raw_label = raw_label
        super().__init__(f"Unexpected classifier label: {raw_label!r}")


# =============================================
# Fallback rules (mirror legacy _classify_intent)
# =============================================

_RE_CHANGE_QUANTITY_1 = re.compile(r"muda\s*para\s*\d+")
_RE_REMOVE_ITEM_1 = re.compile(r"tira\s*\d+")
_RE_ADD_ITEM_1 = re.compile(
    r"coloca\s*\d+\s*(?:kg|quilos|g|gramas|forma|peça|pote|saco|"
    r"garrafa|caixa|barra|bloco|bisnaga)"
)

_ADD_ITEM_KEYWORDS = (
    "quero", "me manda", "coloca", "bota", "manda", "gostaria",
)
_REMOVE_OR_CANCEL_KEYWORDS = ("tira", "remove", "cancela")
_CHANGE_QUANTITY_KEYWORDS = ("muda", "troca", "na verdade")
_CONFIRM_ORDER_KEYWORDS = ("fecha", "fechar", "confirmar", "confirmado")


def _fallback_recognize(message: str) -> RecognitionResult:
    """
    Deterministic first-match-wins fallback.

    Preserves order and content of the legacy rule set frozen in
    Stage 4I.4a. No opportunistic changes.
    """
    msg = message.lower()

    if _RE_CHANGE_QUANTITY_1.search(msg):
        return RecognitionResult(
            RecognitionOutcome.RECOGNIZED, CommandLabel.CHANGE_QUANTITY
        )
    if _RE_REMOVE_ITEM_1.search(msg):
        return RecognitionResult(
            RecognitionOutcome.RECOGNIZED, CommandLabel.REMOVE_ITEM
        )
    if _RE_ADD_ITEM_1.search(msg):
        return RecognitionResult(
            RecognitionOutcome.RECOGNIZED, CommandLabel.ADD_ITEM
        )
    if any(w in msg for w in _ADD_ITEM_KEYWORDS):
        return RecognitionResult(
            RecognitionOutcome.RECOGNIZED, CommandLabel.ADD_ITEM
        )
    if any(w in msg for w in _REMOVE_OR_CANCEL_KEYWORDS):
        if "tudo" in msg or "pedido" in msg:
            return RecognitionResult(
                RecognitionOutcome.RECOGNIZED, CommandLabel.CANCEL_ORDER
            )
        return RecognitionResult(
            RecognitionOutcome.RECOGNIZED, CommandLabel.REMOVE_ITEM
        )
    if any(w in msg for w in _CHANGE_QUANTITY_KEYWORDS):
        return RecognitionResult(
            RecognitionOutcome.RECOGNIZED, CommandLabel.CHANGE_QUANTITY
        )
    if any(w in msg for w in _CONFIRM_ORDER_KEYWORDS):
        return RecognitionResult(
            RecognitionOutcome.RECOGNIZED, CommandLabel.CONFIRM_ORDER
        )
    return RecognitionResult(RecognitionOutcome.UNRECOGNIZED)


# =============================================
# Classifier output extraction
# =============================================

_MALFORMED_OUTPUT = object()


def _extract_label_if_present(output):
    """
    Extract the label string from a transformers-style classifier
    output ([{"label": ..., "score": ...}]).

    Returns _MALFORMED_OUTPUT for anything that does not fit that
    shape. Malformed output is treated like classifier failure and
    falls through to the deterministic fallback (legacy behavior).
    """
    if not isinstance(output, list) or not output:
        return _MALFORMED_OUTPUT
    first = output[0]
    if not isinstance(first, dict) or "label" not in first:
        return _MALFORMED_OUTPUT
    return first["label"]


ClassifierCallable = Callable[[str], list]
LabelMap = Mapping[str, Optional[CommandLabel]]


class CommandRecognizer:
    """
    Deterministic COMMAND recognizer.

    Constructor:
        classifier : optional callable(message) -> [{"label": ...}].
            If None, only the deterministic fallback is used.
        label_map  : mapping from classifier label string to either
            a CommandLabel (RECOGNIZED) or None (UNRECOGNIZED).
            Required if classifier is provided.
            Any classifier label not in the map triggers
            UnexpectedClassifierOutput.
    """

    def __init__(
        self,
        classifier: Optional[ClassifierCallable] = None,
        label_map: Optional[LabelMap] = None,
    ) -> None:
        if classifier is not None and label_map is None:
            raise ValueError(
                "label_map is required when classifier is provided"
            )
        self._classifier = classifier
        self._label_map = dict(label_map) if label_map else {}

    def recognize(self, message: str) -> RecognitionResult:
        """
        Recognize a COMMAND label for `message`.

        Behavior:
            - If classifier is None         -> fallback.
            - If classifier raises          -> fallback (legacy).
            - If classifier returns malformed output -> fallback.
            - If classifier returns a label:
                * label in map, mapped to CommandLabel -> RECOGNIZED
                * label in map, mapped to None         -> UNRECOGNIZED
                * label not in map -> UnexpectedClassifierOutput
        """
        if self._classifier is None:
            return _fallback_recognize(message)

        try:
            output = self._classifier(message)
        except Exception:
            # Legacy: classifier operation failure falls through.
            return _fallback_recognize(message)

        raw_label = _extract_label_if_present(output)
        if raw_label is _MALFORMED_OUTPUT:
            # Legacy: malformed classifier output falls through.
            return _fallback_recognize(message)

        if raw_label not in self._label_map:
            raise UnexpectedClassifierOutput(raw_label)

        mapped = self._label_map[raw_label]
        if mapped is None:
            return RecognitionResult(RecognitionOutcome.UNRECOGNIZED)
        return RecognitionResult(RecognitionOutcome.RECOGNIZED, mapped)