from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum

class OutcomeType(Enum):
    OPERATION = "OPERATION"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    BLOCKED = "BLOCKED"
    NO_OP = "NO_OP"

@dataclass
class ResolutionResult:
    outcome: OutcomeType
    operation: Optional[Dict[str, Any]] = None
    reason_code: Optional[str] = None
    evidence: List[str] = field(default_factory=list)