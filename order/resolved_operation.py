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
        """
        Contrato de execução derivado de
        order.operation_fields.EXECUTION_REQUIREMENTS.

        A validação NÃO é reimplementada manualmente aqui. Consulta a
        declaração central para garantir única fonte de verdade.

        Regras:
            - UNKNOWN e demais tipos em NON_EXECUTABLE_OPERATION_TYPES
              são sempre inválidos.
            - Tipos ausentes de EXECUTION_REQUIREMENTS são inválidos
              por padrão (default conservador).
            - Um tipo é válido se TODOS os campos listados em
              EXECUTION_REQUIREMENTS[type] estiverem preenchidos
              (não-None).

        Semântica especial (CHANGE_QUANTITY):
            quantity_unit NÃO aparece em EXECUTION_REQUIREMENTS.
            Quando None, significa KEEP_EXISTING_UNIT — o Order Engine
            preserva a unidade do item existente em OrderState.

        Lazy import: operation_fields importa OperationType deste
        módulo no topo. O import é feito dentro do método para evitar
        ciclo de carregamento.
        """
        from order.operation_fields import (
            EXECUTION_REQUIREMENTS,
            NON_EXECUTABLE_OPERATION_TYPES,
        )

        if self.type in NON_EXECUTABLE_OPERATION_TYPES:
            return False

        required = EXECUTION_REQUIREMENTS.get(self.type)
        if required is None:
            # Tipo sem entrada explícita na tabela de execução.
            return False

        for field_name in required:
            if getattr(self, field_name, None) is None:
                return False

        return True