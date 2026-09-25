"""
ORDO — Command Evidence Provider contract (Track 10, Stage 4I.2).

Abstract interface by which the future application layer will obtain
CommandEvidence for a given message.

Scope:
    - Contract only. No concrete provider.
    - No recognizer. No wrapper. No regex. No mapping.
    - No integration with any adapter.

Principles honored:
    T10-P26  COMMAND EVIDENCE != COMMAND INTENT
    T10-P27  UNKNOWN recognition != ABSENT
    T10-P28  ABSENT requires positive negative evidence
    T10-P31  UNKNOWN classification != unexpected value
    T10-P32  EvidenceProvider != Recognizer Owner

Failure contract:
    - evaluated           -> CommandEvidence
    - operational failure -> explicit exception (never a value)

This module does NOT:
    - import any adapter, model, or benchmark module;
    - import SemanticIntent, OperationType, QueryType, OrderState,
      OrderEngine, ResolutionResult, or QueryResolutionResult;
    - carry a COMMAND intent;
    - own the recognition strategy for COMMAND;
    - define UNKNOWN -> INDETERMINATE mapping (that belongs to a
      future concrete implementation).
"""
from abc import ABC, abstractmethod

from pipeline.signal_observation import CommandEvidence


class CommandEvidenceProvider(ABC):
    """
    Contract for obtaining COMMAND-domain evidence from a message.

    Implementations define their own recognition strategy. This
    contract does not define, own, or constrain it (T10-P32).
    """

    @abstractmethod
    def predict(self, message: str) -> CommandEvidence:
        """
        Return CommandEvidence for `message`.

        Semantics:
            - sufficient evidence to offer to the COMMAND pipeline
                                            -> CommandEvidence.PRESENT
            - positive evidence of NOT belonging to COMMAND
                                            -> CommandEvidence.ABSENT
            - no conclusion reached             -> CommandEvidence.INDETERMINATE
            - operational failure               -> raise (never return)

        Note (T10-P26):
            PRESENT does NOT carry which operation exists. That
            remains the responsibility of the COMMAND resolution
            pipeline.

        Note (T10-P27):
            An "UNKNOWN" recognizer output maps to INDETERMINATE,
            never to ABSENT. That mapping belongs to a concrete
            implementation, not to this contract.

        Note (T10-P28):
            ABSENT may only be emitted with positive evidence of
            non-membership. Implementations that lack such evidence
            simply never emit ABSENT.
        """
        raise NotImplementedError