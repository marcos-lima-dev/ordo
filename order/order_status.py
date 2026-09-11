from enum import Enum

class OrderStatus(Enum):
    OPEN = "OPEN"
    DRAFT = "DRAFT"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    READY_TO_CONFIRM = "READY_TO_CONFIRM"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"

ALLOWED_TRANSITIONS = {
    OrderStatus.OPEN: [
        OrderStatus.DRAFT,
        OrderStatus.NEEDS_CLARIFICATION,
        OrderStatus.READY_TO_CONFIRM,
        OrderStatus.CANCELLED
    ],
    OrderStatus.DRAFT: [
        OrderStatus.NEEDS_CLARIFICATION,
        OrderStatus.READY_TO_CONFIRM,
        OrderStatus.CANCELLED
    ],
    OrderStatus.NEEDS_CLARIFICATION: [
        OrderStatus.DRAFT,
        OrderStatus.READY_TO_CONFIRM,
        OrderStatus.CANCELLED
    ],
    OrderStatus.READY_TO_CONFIRM: [
        OrderStatus.CONFIRMED,
        OrderStatus.CANCELLED
    ],
    OrderStatus.CONFIRMED: [],  # terminal
    OrderStatus.CANCELLED: [],  # terminal
}

def can_transition(current: OrderStatus, target: OrderStatus) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, [])