from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum

from order.resolved_operation import OperationType


class OperationResolutionStatus(Enum):
    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    UNKNOWN = "UNKNOWN"


class OperationSource(Enum):
    CLASSIFIER = "CLASSIFIER"
    DETERMINISTIC_SIGNAL = "DETERMINISTIC_SIGNAL"
    CLASSIFIER_PLUS_CONTEXT = "CLASSIFIER_PLUS_CONTEXT"
    DETERMINISTIC_SIGNAL_PLUS_CONTEXT = "DETERMINISTIC_SIGNAL_PLUS_CONTEXT"
    PENDING_CONTEXT = "PENDING_CONTEXT"
    UNKNOWN = "UNKNOWN"


@dataclass
class OperationResolution:
    message_intent: OperationType
    resolved_operation_type: Optional[OperationType]
    status: OperationResolutionStatus
    source: OperationSource
    evidence: List[str] = field(default_factory=list)


class OperationResolver:
    """
    Resolve o tipo de operação semanticamente sustentado pela mensagem + contexto.

    Não resolve target nem produto.
    Não altera OrderState.
    """

    # Sinais linguísticos determinísticos para operações
    DETERMINISTIC_SIGNALS = [
        (r"\btira\b", OperationType.REMOVE_ITEM),
        (r"\bremove\b", OperationType.REMOVE_ITEM),
        (r"\bretira\b", OperationType.REMOVE_ITEM),
        (r"\bmuda\s+para\b", OperationType.CHANGE_QUANTITY),
        (r"\baltera\s+para\b", OperationType.CHANGE_QUANTITY),
        (r"\btroca\b", OperationType.REPLACE_ITEM),
        (r"\bsubstitui\b", OperationType.REPLACE_ITEM),
        (r"\bcancela\b", OperationType.CANCEL_ORDER),
        (r"\bfecha\b", OperationType.CONFIRM_ORDER),
        (r"\bconfirmar\b", OperationType.CONFIRM_ORDER),
        (r"\bcoloca\b", OperationType.ADD_ITEM),
        (r"\badiciona\b", OperationType.ADD_ITEM),
        (r"\bquero\b", OperationType.ADD_ITEM),
    ]

    def resolve(self, message: str, classifier_intent: OperationType) -> OperationResolution:
        msg_lower = message.lower()

        # 1. Detecta sinais determinísticos
        deterministic_signals = []
        for pattern, op_type in self.DETERMINISTIC_SIGNALS:
            import re
            if re.search(pattern, msg_lower):
                deterministic_signals.append(op_type)

        deterministic_signals = list(dict.fromkeys(deterministic_signals))  # unique preservando ordem

        # 2. Sem sinais determinísticos: usa o classificador
        if not deterministic_signals:
            return OperationResolution(
                message_intent=classifier_intent,
                resolved_operation_type=classifier_intent,
                status=OperationResolutionStatus.RESOLVED,
                source=OperationSource.CLASSIFIER,
                evidence=["no_deterministic_signal"],
            )

        # 3. Se o sinal determinístico é único e compatível com o classificador
        if len(deterministic_signals) == 1:
            det = deterministic_signals[0]
            if det == classifier_intent:
                return OperationResolution(
                    message_intent=classifier_intent,
                    resolved_operation_type=det,
                    status=OperationResolutionStatus.RESOLVED,
                    source=OperationSource.CLASSIFIER_PLUS_CONTEXT,
                    evidence=[f"classifier={classifier_intent.value}", f"deterministic={det.value}"],
                )
            # Sinal determinístico é mais específico: prevalece
            return OperationResolution(
                message_intent=classifier_intent,
                resolved_operation_type=det,
                status=OperationResolutionStatus.RESOLVED,
                source=OperationSource.DETERMINISTIC_SIGNAL,
                evidence=[f"classifier={classifier_intent.value}", f"deterministic_override={det.value}"],
            )

        # 4. Múltiplos sinais determinísticos conflitantes
        return OperationResolution(
            message_intent=classifier_intent,
            resolved_operation_type=None,
            status=OperationResolutionStatus.AMBIGUOUS,
            source=OperationSource.DETERMINISTIC_SIGNAL,
            evidence=[f"conflicting_signals={[s.value for s in deterministic_signals]}"],
        )