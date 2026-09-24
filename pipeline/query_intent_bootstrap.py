"""
ORDO — Query Intent Bootstrap (Track 10, Stage 4G).

Provisional deterministic bootstrap implementation of
QueryIntentProvider for QUERY recognition.

Status: PROVISIONAL.
    Replaceable by an evidence/data-driven provider. Not a permanent
    contract. No ML. No external dependencies. No heuristics beyond
    the explicitly authorized lexical rules.

Scope:
    - Emits QUERY_PRICE, QUERY_AVAILABILITY, or UNRESOLVED.
    - Does NOT emit NOT_QUERY (declared GAP for this bootstrap).
    - Does NOT recognize COMMAND (T10-P14).
    - Does NOT resolve product, catalog, or state.

Principles honored:
    T10-P9   PROVIDER SIGNAL != SEMANTIC INTENT
    T10-P10  NOT_QUERY is a positive negative classification
    T10-P11  absence of query evidence != NOT_QUERY
    T10-P12  UNRESOLVED != provider failure
    T10-P13  UNRESOLVED != NOT_QUERY
    T10-P14  QUERY PROVIDER DOES NOT VETO ON COMMAND SEMANTICS
    T10-P15  STRUCTURAL PUNCTUATION != SEMANTIC CONFLICT EVIDENCE

Failure contract:
    - evaluated           -> QueryIntentSignal
    - operational failure -> exception (never a signal)
"""
from __future__ import annotations

import re
import unicodedata

from pipeline.query_intent_provider import (
    QueryIntentProvider,
    QueryIntentSignal,
)

# ---------------------------------------------------------------------
# Regexes over normalized text (lowercase, no accents).
# ---------------------------------------------------------------------

# Strong PRICE evidence.
_RE_PRICE_QUANTO_CUSTA = re.compile(r"\bquanto\s+custa\b")
_RE_PRICE_PRECO = re.compile(r"\bpreco\b")
_RE_PRICE_VALOR_QUAL = re.compile(r"\bqual\s+(?:o|e\s+o)\s+valor\b")

# Strong AVAILABILITY evidence. Not anchored, so structural
# punctuation elsewhere in the message (T10-P15) does not affect
# matching.
_RE_AVAIL_DISPONIVEL = re.compile(r"\bdisponivel\b")
_RE_AVAIL_SUBJECT_TEM = re.compile(r"\b(?:voce|voces|vc)\s+tem\s+[a-z0-9]+")
_RE_AVAIL_TEM_ONE_NOUN = re.compile(r"\btem\s+[a-z0-9]+")

# Ambiguity probes (QUERY-domain only).
_RE_HAS_VALOR = re.compile(r"\bvalor\b")
_RE_HAS_QUANTO = re.compile(r"\bquanto\b")
_RE_HAS_DE_QUANTO = re.compile(r"\bde\s+quanto\b")
_RE_HAS_COMO = re.compile(r"\bcomo\b")
_RE_HAS_TEM = re.compile(r"\btem\b")


def _normalize(text: str) -> str:
    """
    Lexical normalization only:
        - NFD decomposition + accent stripping
        - lowercase
        - collapse whitespace
        - strip

    Structural punctuation is not semantic evidence (T10-P15);
    it is handled by _strip_trivial_punct for matching purposes only.
    """
    if not isinstance(text, str):
        raise TypeError(
            "QueryIntentBootstrap.predict expects str, got "
            f"{type(text).__name__}"
        )
    decomposed = unicodedata.normalize("NFD", text)
    without_marks = "".join(
        ch for ch in decomposed if unicodedata.category(ch) != "Mn"
    )
    lowered = without_marks.lower()
    collapsed = re.sub(r"\s+", " ", lowered)
    return collapsed.strip()


def _strip_trivial_punct(text: str) -> str:
    """
    Remove '?' '!' '.' for structural matching.

    Structural punctuation is not semantic evidence (T10-P15).
    """
    return re.sub(r"[?!.]+", "", text)


class QueryIntentBootstrap(QueryIntentProvider):
    """
    Provisional deterministic bootstrap provider.

    Public API: `predict(message: str) -> QueryIntentSignal`.
    """

    def predict(self, message: str) -> QueryIntentSignal:
        normalized = _normalize(message)
        if not normalized:
            return QueryIntentSignal.UNRESOLVED

        structural = _strip_trivial_punct(normalized)
        structural = re.sub(r"\s+", " ", structural).strip()

        # --- PRICE evidence ---
        has_price = bool(
            _RE_PRICE_QUANTO_CUSTA.search(structural)
            or _RE_PRICE_PRECO.search(structural)
            or _RE_PRICE_VALOR_QUAL.search(structural)
        )

        # --- AVAILABILITY evidence ---
        has_availability = bool(
            _RE_AVAIL_DISPONIVEL.search(structural)
            or _RE_AVAIL_SUBJECT_TEM.search(structural)
            or _RE_AVAIL_TEM_ONE_NOUN.search(structural)
        )

        # --- Ambiguity flags (QUERY-domain only) ---
        has_valor_unaligned = bool(
            _RE_HAS_VALOR.search(structural)
        ) and not bool(_RE_PRICE_VALOR_QUAL.search(structural))

        has_quanto_not_custa = bool(
            _RE_HAS_QUANTO.search(structural)
        ) and not bool(_RE_PRICE_QUANTO_CUSTA.search(structural))

        has_de_quanto = bool(_RE_HAS_DE_QUANTO.search(structural))
        has_como = bool(_RE_HAS_COMO.search(structural))
        has_tem = bool(_RE_HAS_TEM.search(structural))

        tem_unmatched = has_tem and not has_availability

        ambiguous = (
            has_valor_unaligned
            or has_quanto_not_custa
            or has_de_quanto
            or has_como
            or tem_unmatched
        )

        if has_price and has_availability:
            return QueryIntentSignal.UNRESOLVED
        if has_price and not ambiguous:
            return QueryIntentSignal.QUERY_PRICE
        if has_availability and not ambiguous and not has_price:
            return QueryIntentSignal.QUERY_AVAILABILITY
        return QueryIntentSignal.UNRESOLVED