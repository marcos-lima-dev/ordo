"""
ORDO — Shared entity extractor (multi-item safety gate).

Thin, reusable wrapper around GLiNER entity extraction. Single point
of truth for raw entity extraction used by safety components.

Design:
    - Model instance is loaded lazily via a module-level cache,
      keyed by model name.
    - An explicit `model` may be injected (tests, future providers).
    - Extraction is stateless: input message, output raw entities.
    - No safety policy, no classification, no commercial resolution.

This module does NOT:
    - decide anything about safety;
    - resolve product, quantity, or operation;
    - know about REPRESENTATIONAL_OVERFLOW or any reason code;
    - own OrderState, OrderEngine, or any pipeline.
"""
from __future__ import annotations

from typing import Dict, Iterable, List

from gliner import GLiNER


_DEFAULT_MODEL = "urchade/gliner_medium"
_INSTANCES: Dict[str, object] = {}


def _get_instance(model_name: str):
    if model_name not in _INSTANCES:
        _INSTANCES[model_name] = GLiNER.from_pretrained(model_name)
    return _INSTANCES[model_name]


class EntityExtractor:
    """
    Thin wrapper around GLiNER entity extraction.

    The underlying model is loaded lazily and cached per-process,
    keyed by model name. An explicit `model` may be injected.
    """

    def __init__(self, model=None, *, model_name: str = _DEFAULT_MODEL):
        self._model = model if model is not None else _get_instance(model_name)

    def extract_entities(
        self,
        message: str,
        labels: Iterable[str],
        *,
        threshold: float = 0.3,
    ) -> List[dict]:
        """
        Return the raw GLiNER output for `message` over `labels`.
        """
        return list(
            self._model.predict_entities(
                message, list(labels), threshold=threshold,
            )
        )