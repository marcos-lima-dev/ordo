"""
ORDO — Canonical command execution composition (post-Track-10).

Composes the canonical COMMAND execution path:

    CallerResult.command (ResolutionResult | None)
        -> to_resolved_operation()
        -> if not executable: stop
        -> execute_resolution()
        -> OrderEngine.apply()
        -> OrderState + events

Three distinct states are preserved:

    NOT_INVOKED      -- no COMMAND was invoked by the application caller
    NOT_EXECUTABLE   -- COMMAND present but boundary rejected it
    EXECUTED         -- execute_resolution() was actually called

Principles honored:
    P56  COMMAND EXECUTION STATUS COMES FROM CONTROL FLOW, NOT ENGINE EVENTS
    P57  EXECUTION COMPOSITION DOES NOT OWN STATE
    P58  BOUNDARY RECHECK DOES NOT CREATE A SECOND AUTHORITY

This module does NOT:
    - mutate OrderState directly;
    - call OrderEngine.apply directly (always through execute_resolution);
    - own sessions, persistence, or serialization;
    - touch the QUERY side;
    - use legacy processors (ConversationProcessor, HybridPipelineV1/V2).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional, Tuple

from order.engine import OrderEngine
from order.execution import execute_resolution
from order.resolution_boundary import to_resolved_operation
from order.resolution_result import ResolutionResult
from order.state import OrderState

from pipeline.application_caller import CallerResult


class CommandExecutionStatus(Enum):
    NOT_INVOKED = "NOT_INVOKED"
    NOT_EXECUTABLE = "NOT_EXECUTABLE"
    EXECUTED = "EXECUTED"


@dataclass(frozen=True)
class CommandExecutionResult:
    """
    Result of composing the canonical COMMAND execution.

    status: derived from control flow, never from events (P56).
    resolution_result: present iff caller_result.command was not None.
    state: present only when status is EXECUTED.
    events: whatever execute_resolution returned; may be empty.
    """
    status: CommandExecutionStatus
    resolution_result: Optional[ResolutionResult] = None
    state: Optional[OrderState] = None
    events: Tuple[str, ...] = ()


def compose_command_execution(
    caller_result: CallerResult,
    state: OrderState,
    engine: OrderEngine,
    *,
    to_resolved_operation_fn: Callable = to_resolved_operation,
    execute_resolution_fn: Callable = execute_resolution,
) -> CommandExecutionResult:
    """
    Compose the canonical COMMAND execution from a CallerResult.

    Only reads ``caller_result.command``. The ``query`` field is not
    inspected or propagated.

    The pre-validation via ``to_resolved_operation_fn`` exists only
    to classify NOT_EXECUTABLE vs EXECUTED (P58). It is a pure call
    with no side effects. ``execute_resolution`` performs its own
    defensive validation normally.
    """
    cmd = caller_result.command
    if cmd is None:
        return CommandExecutionResult(
            status=CommandExecutionStatus.NOT_INVOKED,
        )

    if to_resolved_operation_fn(cmd) is None:
        return CommandExecutionResult(
            status=CommandExecutionStatus.NOT_EXECUTABLE,
            resolution_result=cmd,
        )

    new_state, events = execute_resolution_fn(state, cmd, engine)
    return CommandExecutionResult(
        status=CommandExecutionStatus.EXECUTED,
        resolution_result=cmd,
        state=new_state,
        events=tuple(events),
    )