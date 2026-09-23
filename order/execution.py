"""
ORDO — Canonical execution caller (Track 9C, Stage 3A).

Wraps the ResolutionResult → ResolvedOperation → OrderEngine chain in
a single deterministic entry point.

Contract:
    - receives a ResolutionResult;
    - delegates handoff eligibility to the official boundary
      (``to_resolved_operation``);
    - calls the OrderEngine only when the boundary returns a valid
      ResolvedOperation;
    - returns ``(state, [])`` when the boundary rejected the result.

Architectural guarantee (not reciprocal, not inferred from events):

    boundary returns None
        ⇒
    Engine is NOT called
        ⇒
    execute_resolution returns (state, [])

Callers must NOT infer "Engine was executed" or "Engine was not
executed" from the cardinality of the returned events list. The proof
that execution did or did not happen belongs to the control path, not
to the length of the events list.

This module does NOT:
    - interpret language;
    - consult catalog;
    - choose product or target;
    - resolve references;
    - infer quantity or unit;
    - invent source_message_id or evidence;
    - fix or reinterpret ResolutionResult;
    - reinterpret UNKNOWN;
    - duplicate is_valid() or EXECUTION_REQUIREMENTS.

Architectural separation preserved:
    resolution (pipeline)  !=  execution boundary (this module)
"""
from typing import List, Tuple

from order.engine import OrderEngine
from order.resolution_boundary import to_resolved_operation
from order.resolution_result import ResolutionResult
from order.state import OrderState


def execute_resolution(
    state: OrderState,
    result: ResolutionResult,
    engine: OrderEngine,
) -> Tuple[OrderState, List[str]]:
    """
    Execute a ResolutionResult against an OrderState via the canonical
    boundary and the OrderEngine.

    Eligibility is delegated entirely to ``to_resolved_operation``. No
    validity checks or execution requirements are duplicated here.

    Returns:
        (OrderState, List[str])
            - If the boundary returns a valid ResolvedOperation:
              the result of ``engine.apply(state, operation)``.
            - Otherwise: ``(state, [])`` — the original state, unchanged.

    Deterministic. Does not mutate ``result``. Does not fabricate
    metadata. Does not bypass the boundary.
    """
    operation = to_resolved_operation(result)
    if operation is None:
        return state, []
    return engine.apply(state, operation)