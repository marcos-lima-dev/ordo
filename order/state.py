from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from .pending import PendingResolution

@dataclass
class OrderItem:
    """Representa um item no pedido."""
    product_term: str                      # termo original do cliente
    product_id: Optional[str] = None       # SKU resolvido (CQ-XX)
    quantity: Optional[float] = None
    unit: Optional[str] = None
    brand: Optional[str] = None
    presentation: Optional[str] = None
    resolved: bool = False                 # se foi resolvido contra o catálogo
    needs_clarification: bool = False      # se precisa de mais informações
    clarification_questions: List[str] = field(default_factory=list)
    id: Optional[str] = None               # identificador único do item no pedido

@dataclass
class OrderState:
    """Estado completo do pedido durante uma conversa."""
    items: List[OrderItem] = field(default_factory=list)
    status: str = "OPEN"  # OPEN | NEEDS_CLARIFICATION | CONFIRMED | CANCELED
    pending_clarifications: List[str] = field(default_factory=list)
    last_message: Optional[str] = None
    turn_count: int = 0

    # NOVO: resolução pendente (para contexto conversacional)
    pending_resolution: Optional[PendingResolution] = None

    # Contador interno para gerar IDs únicos
    _item_counter: int = field(default=0, init=False, repr=False)

    def add_item(self, item: OrderItem) -> None:
        """Adiciona um item ao pedido, atribuindo um ID único."""
        self._item_counter += 1
        if item.id is None:
            item.id = f"item_{self._item_counter}"
        self.items.append(item)

    def remove_item(self, index: int) -> None:
        """Remove um item pelo índice."""
        if 0 <= index < len(self.items):
            self.items.pop(index)

    def remove_item_by_id(self, item_id: str) -> bool:
        """Remove um item pelo ID. Retorna True se encontrado e removido."""
        for i, item in enumerate(self.items):
            if item.id == item_id:
                self.items.pop(i)
                return True
        return False

    def update_item(self, index: int, **kwargs) -> None:
        """Atualiza campos de um item pelo índice."""
        if 0 <= index < len(self.items):
            for key, value in kwargs.items():
                if hasattr(self.items[index], key) and key != "id":
                    setattr(self.items[index], key, value)

    def update_item_by_id(self, item_id: str, **kwargs) -> bool:
        """Atualiza um item pelo ID. Retorna True se encontrado e atualizado."""
        for item in self.items:
            if item.id == item_id:
                for key, value in kwargs.items():
                    if hasattr(item, key) and key != "id":
                        setattr(item, key, value)
                return True
        return False

    def find_item_by_term(self, term: str) -> Optional[OrderItem]:
        """Encontra o primeiro item cujo product_term contenha o termo."""
        term_lower = term.lower()
        for item in self.items:
            if term_lower in item.product_term.lower():
                return item
        return None

    def find_item_by_id(self, item_id: str) -> Optional[OrderItem]:
        """Encontra um item pelo ID."""
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def set_pending(self, pending: PendingResolution) -> None:
        """Define uma resolução pendente."""
        self.pending_resolution = pending
        self.status = "NEEDS_CLARIFICATION"

    def clear_pending(self) -> None:
        """Limpa a resolução pendente."""
        self.pending_resolution = None
        # Se não houver outras pendências, volta para OPEN
        if not self.pending_clarifications:
            self.status = "OPEN"

    def to_dict(self) -> Dict[str, Any]:
        """Converte o estado para um dicionário serializável."""
        return {
            "items": [item.__dict__ for item in self.items],
            "status": self.status,
            "pending_clarifications": self.pending_clarifications,
            "turn_count": self.turn_count,
            "pending_resolution": self.pending_resolution.__dict__ if self.pending_resolution else None,
        }