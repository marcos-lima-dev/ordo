from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum

class OperationType(Enum):
    ADD_ITEM = "ADD_ITEM"
    REMOVE_ITEM = "REMOVE_ITEM"
    CHANGE_QUANTITY = "CHANGE_QUANTITY"
    REPLACE_ITEM = "REPLACE_ITEM"
    CONFIRM_ORDER = "CONFIRM_ORDER"
    CANCEL_ORDER = "CANCEL_ORDER"
    UNKNOWN = "UNKNOWN"   # <-- ADICIONADO

@dataclass
class ResolvedOperation:
    type: OperationType
    product_id: Optional[str] = None
    product_term: Optional[str] = None
    target_item_id: Optional[str] = None
    quantity_value: Optional[float] = None
    quantity_unit: Optional[str] = None
    replacement_product_id: Optional[str] = None
    source_message_id: Optional[str] = None
    evidence: List[str] = field(default_factory=list)

    def is_valid(self) -> bool:
        if self.type == OperationType.UNKNOWN:
            return False
        if self.type == OperationType.ADD_ITEM:
            return self.product_id is not None or self.product_term is not None
        if self.type == OperationType.REMOVE_ITEM:
            return self.target_item_id is not None
        if self.type == OperationType.CHANGE_QUANTITY:
            return self.target_item_id is not None and self.quantity_value is not None
        if self.type == OperationType.REPLACE_ITEM:
            return self.target_item_id is not None and self.replacement_product_id is not None
        if self.type in [OperationType.CONFIRM_ORDER, OperationType.CANCEL_ORDER]:
            return True
        return False