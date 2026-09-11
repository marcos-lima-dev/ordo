from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict

class ReferenceType(Enum):
    EXPLICIT_REFERENCE = "EXPLICIT_REFERENCE"   # menção direta a um produto/item
    PENDING_REFERENCE = "PENDING_REFERENCE"     # referência a um item pendente
    GENERIC_REFERENCE = "GENERIC_REFERENCE"     # "esse", "aquele", "o outro"
    UNKNOWN = "UNKNOWN"                         # sem referência clara

@dataclass
class ReferenceSignal:
    type: ReferenceType
    constraints: Dict[str, str] = field(default_factory=dict)  # {"brand": "Tânia", "presentation": "forma", etc.}
    evidence: List[str] = field(default_factory=list)          # lista de evidências que levaram àquele sinal
    requires_clarification: bool = False
    item_id: Optional[str] = None                              # se a referência for a um item existente
    product_term: Optional[str] = None                         # se a referência for a um produto específico