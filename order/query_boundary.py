"""
ORDO — Official QueryResolutionResult → ResolvedQuery boundary.

Track 10 — Stage 3.

PURE MAPPING. Sem interpretação, sem catalog lookup, sem acesso a
OrderState, sem inferência, sem efeitos colaterais.

Pipeline conceitual:

    QueryResolutionResult (status=RESOLVED)
            ↓
    validate handoff eligibility
            ↓
    map already-resolved fields
            ↓
    ResolvedQuery (ou None)

Pós-condição:
    se retornar ResolvedQuery, is_valid() == True.

Runtime validation:
    - status must be QueryResolutionStatus.RESOLVED
    - query_type must be an instance of QueryType (no coercion)
    - product_id must be non-None
    - resulting ResolvedQuery must satisfy is_valid()

Esta boundary NÃO:
    - interpreta linguagem;
    - executa catalog lookup;
    - resolve produto, target, unidade ou quantidade;
    - escolhe candidatos, aplica alias ou resolve ambiguidade;
    - consulta OrderState para completar semântica;
    - executa regra comercial;
    - cria pending / pendência de query;
    - transforma NEEDS_CLARIFICATION em query executável;
    - converte strings em enums, nem aplica fallback/reparo.

Princípio (Track 10 Stage 3):
    BOUNDARY = VALIDATE + CONVERT
    BOUNDARY ≠ REPAIR + RESOLVE

Decisão explícita sobre evidence (Track 10 Stage 3):
    QueryResolutionResult.evidence NÃO é propagado automaticamente
    para ResolvedQuery.evidence. Consistente com a disciplina
    aprendida no Track 9C (Stage 2): a boundary decide, não assume.
    Nesta implementação, evidence é deixado no default vazio.

Não depende de:
    - order.engine
    - order.state
    - order.operation_fields
    - order.catalog_retriever
    - order.product_resolver
"""
from typing import Optional

from order.query_resolution_result import (
    QueryResolutionResult,
    QueryResolutionStatus,
)
from order.resolved_query import QueryType, ResolvedQuery


def to_resolved_query(result: QueryResolutionResult) -> Optional[ResolvedQuery]:
    """
    Converte uma QueryResolutionResult resolvida em ResolvedQuery.

    Determinística. Sem efeitos colaterais. Não muta ``result``.

    Retorna ``None`` quando a QueryResolutionResult não é elegível
    para handoff:
      - ``status != RESOLVED``;
      - ``query_type`` não é instância de ``QueryType``
        (sem coerção de string, sem fallback);
      - ``product_id`` ausente ou None;
      - a query resultante não satisfaz ``is_valid()``.

    Não realiza inferência. Não consulta OrderState nem catálogo.
    Não propaga evidence automaticamente (ver docstring do módulo).
    """
    if result.status != QueryResolutionStatus.RESOLVED:
        return None

    # Runtime type validation (QB-07): query_type must be a QueryType
    # instance. No string conversion, no enum coercion, no fallback.
    if not isinstance(result.query_type, QueryType):
        return None

    if result.product_id is None:
        return None

    rq = ResolvedQuery(
        query_type=result.query_type,
        product_id=result.product_id,
        # evidence NOT propagated — boundary decision (Track 10 Stage 3)
    )

    # Pós-condição obrigatória: nunca retornar query inválida.
    if not rq.is_valid():
        return None

    return rq