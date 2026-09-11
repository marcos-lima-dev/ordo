from dataclasses import dataclass, field
from typing import Optional, List
from .state import OrderState
from .pending import PendingResolution
from .target import TargetType

@dataclass
class ResolutionContext:
    active_item_id: Optional[str] = None
    pending_resolution: Optional[PendingResolution] = None
    recent_items: List[str] = field(default_factory=list)
    unresolved_references: List[str] = field(default_factory=list)

    @classmethod
    def from_order_state(cls, state: OrderState) -> "ResolutionContext":
        return cls(
            active_item_id=state.items[-1].product_term if state.items else None,
            pending_resolution=state.pending_resolution,
            recent_items=[item.product_term for item in state.items[-3:]],
            unresolved_references=[]
        )