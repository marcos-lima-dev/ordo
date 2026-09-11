# order/pending.py
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class PendingResolution:
    """
    Representa uma resolução pendente aguardando informação adicional.
    """
    product_term: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    brand: Optional[str] = None
    presentation: Optional[str] = None
    missing_fields: List[str] = field(default_factory=list)
    reason: str = "AMBIGUOUS_PRODUCT"  # "AMBIGUOUS_PRODUCT", "MISSING_BRAND", etc.
    candidates: List[str] = field(default_factory=list)  # CQ-XX IDs