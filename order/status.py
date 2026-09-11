from enum import Enum

class ClarificationStatus(Enum):
    """Possíveis estados de esclarecimento de um item."""
    RESOLVED = "RESOLVED"
    NEEDS_BRAND = "NEEDS_BRAND"
    NEEDS_PRESENTATION = "NEEDS_PRESENTATION"
    NEEDS_UNIT = "NEEDS_UNIT"
    NEEDS_QUANTITY = "NEEDS_QUANTITY"
    NEEDS_PRODUCT_SPECIFICATION = "NEEDS_PRODUCT_SPECIFICATION"
    AMBIGUOUS_CANDIDATES = "AMBIGUOUS_CANDIDATES"
    NOT_FOUND = "NOT_FOUND"

class OrderStatus(Enum):
    """Possíveis estados do pedido completo."""
    OPEN = "OPEN"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    CONFIRMED = "CONFIRMED"
    CANCELED = "CANCELED"