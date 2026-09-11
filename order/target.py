from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List

class TargetType(Enum):
    EXPLICIT_REFERENCE = "EXPLICIT_REFERENCE"   # menção direta a um produto/item
    PENDING_ITEM = "PENDING_ITEM"               # item pendente de resolução
    EXISTING_ITEM = "EXISTING_ITEM"             # item já no pedido
    ORDER = "ORDER"                             # o pedido como um todo
    UNKNOWN = "UNKNOWN"                         # sem alvo claro

@dataclass
class Target:
    type: TargetType
    item_id: Optional[str] = None
    product_term: Optional[str] = None
    brand_constraint: Optional[str] = None
    presentation_constraint: Optional[str] = None
    evidence: List[str] = field(default_factory=list)
    requires_clarification: bool = False

    def is_resolved(self) -> bool:
        return self.type != TargetType.UNKNOWN and not self.requires_clarification