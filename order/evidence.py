"""
P105 — EVIDENCE REPRESENTATION ≠ RESOLUTION AUTHORITY.

Evidence records observable facts about how and from where a match was
produced. It does NOT carry authority to resolve commercial identity.
That authority is a policy applied separately by ProductResolver.

v0 scope (Correction 2):
    match_kind ∈ {"ALIAS", "NAME", "ORIGINAL_NAME"}
    APPROVED_ALIAS / ENTITY_SIGNAL: no producer exists; not modeled.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Evidence:
    sku: str                    # "CQ-XX"
    stream: str                 # "ORIGINAL" | "NORMALIZED"
    match_kind: str             # "ALIAS" | "NAME" | "ORIGINAL_NAME"
    match_strength: str         # "EXACT" | "TOKEN" | "SUBSET" | "FUZZY"
    source: Optional[str] = None       # meaningful only when match_kind == "ALIAS"
    approved: Optional[bool] = None    # meaningful only when match_kind == "ALIAS"