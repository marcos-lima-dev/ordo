"""
ORDO — Official ResolutionResult → ResolvedOperation boundary.

Track 9C — Stage 2.

PURE MAPPING. Sem interpretação, sem catalog lookup, sem acesso a
OrderState, sem inferência, sem efeitos colaterais.

Pipeline conceitual:

    ResolutionResult (outcome=OPERATION)
            ↓
    validate handoff eligibility
            ↓
    map already-resolved fields
            ↓
    ResolvedOperation (ou None)

Pós-condição:
    se retornar ResolvedOperation, is_valid() == True.

Esta boundary NÃO:
    - interpreta linguagem;
    - executa catalog lookup;
    - resolve produto, target, unidade ou quantidade;
    - escolhe candidatos, aplica alias ou resolve ambiguidade;
    - consulta OrderState para completar semântica;
    - executa regra comercial;
    - cria PendingResolution;
    - transforma NEEDS_CLARIFICATION em operação executável.

Chamada canônica: ``to_resolved_operation(result)``.
"""
from typing import Optional

from order.resolution_result import ResolutionResult, OutcomeType
from order.resolved_operation import ResolvedOperation, OperationType


def to_resolved_operation(result: ResolutionResult) -> Optional[ResolvedOperation]:
    """
    Converte uma ResolutionResult executável em ResolvedOperation.

    Determinística. Sem efeitos colaterais. Não muta ``result``.

    Retorna ``None`` quando a ResolutionResult não é elegível para
    handoff executável:

      - ``outcome != OPERATION``;
      - ``operation`` ausente ou não-dict;
      - ``operation["type"]`` ausente, não-str ou desconhecido;
      - a operação resultante não satisfaz ``is_valid()``.

    Não realiza inferência. Não consulta OrderState nem catálogo.
    Não cria PendingResolution. Campos ausentes no dict tornam-se
    ``None`` na ResolvedOperation e são validados por ``is_valid()``.
    """
    if result.outcome != OutcomeType.OPERATION:
        return None

    op_dict = result.operation
    if not isinstance(op_dict, dict):
        return None

    type_str = op_dict.get("type")
    if not isinstance(type_str, str):
        return None

    try:
        op_type = OperationType(type_str)
    except ValueError:
        return None

    op = ResolvedOperation(
        type=op_type,
        product_id=op_dict.get("product_id"),
        product_term=op_dict.get("product_term"),
        target_item_id=op_dict.get("target_item_id"),
        quantity_value=op_dict.get("quantity_value"),
        quantity_unit=op_dict.get("quantity_unit"),
        replacement_product_id=op_dict.get("replacement_product_id"),
        source_message_id=None,  # RESERVED / NON-OPERATIONAL (P6)
    )

    # Pós-condição obrigatória: nunca retornar operação inválida
    # esperando que o Engine a rejeite depois.
    if not op.is_valid():
        return None

    return op