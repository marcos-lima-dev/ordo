from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum
import re

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
    DETERMINISTIC_SIGNALS = [
        (r"\btira\b", OperationType.REMOVE_ITEM),
        (r"\bremove\b", OperationType.REMOVE_ITEM),
        (r"\bretira\b", OperationType.REMOVE_ITEM),
        (r"\btroca\b", OperationType.REPLACE_ITEM),
        (r"\bsubstitui\b", OperationType.REPLACE_ITEM),
        (r"\bcancela\b", OperationType.CANCEL_ORDER),
        (r"\bfecha\b", OperationType.CONFIRM_ORDER),
        (r"\bconfirmar\b", OperationType.CONFIRM_ORDER),
        (r"\bcoloca\b", OperationType.ADD_ITEM),
        (r"\badiciona\b", OperationType.ADD_ITEM),
        (r"\bquero\b", OperationType.ADD_ITEM),
    ]

    CHANGE_VERBS = [
        r"\bmuda\b",
        r"\bmudar\b",
        r"\baltera\b",
        r"\balterar\b",
        r"\bajusta\b",
        r"\bajustar\b",
    ]

    NUMBER_WORDS = [
        "um", "uma", "dois", "duas", "três", "tres",
        "quatro", "cinco", "seis", "sete", "oito", "nove", "dez",
    ]

    def resolve(self, message: str, classifier_intent: OperationType) -> OperationResolution:
        msg_lower = message.lower()
        deterministic_signals = []

        # Regra composta 9A: change verb + quantity evidence
        if self._has_change_verb(msg_lower) and self._has_quantity_evidence(msg_lower):
            deterministic_signals.append(OperationType.CHANGE_QUANTITY)

        # Sinais simples
        for pattern, op_type in self.DETERMINISTIC_SIGNALS:
            if re.search(pattern, msg_lower):
                deterministic_signals.append(op_type)

        # Remove duplicatas preservando ordem
        deterministic_signals = list(dict.fromkeys(deterministic_signals))

        # Sem sinais determinísticos → classificador decide
        if not deterministic_signals:
            return OperationResolution(
                message_intent=classifier_intent,
                resolved_operation_type=classifier_intent,
                status=OperationResolutionStatus.RESOLVED,
                source=OperationSource.CLASSIFIER,
                evidence=["no_deterministic_signal"],
            )

        # Sinal único
        if len(deterministic_signals) == 1:
            det = deterministic_signals[0]
            if det == classifier_intent:
                return OperationResolution(
                    message_intent=classifier_intent,
                    resolved_operation_type=det,
                    status=OperationResolutionStatus.RESOLVED,
                    source=OperationSource.CLASSIFIER_PLUS_CONTEXT,
                    evidence=[
                        f"classifier={classifier_intent.value}",
                        f"deterministic={det.value}",
                    ],
                )
            return OperationResolution(
                message_intent=classifier_intent,
                resolved_operation_type=det,
                status=OperationResolutionStatus.RESOLVED,
                source=OperationSource.DETERMINISTIC_SIGNAL,
                evidence=[
                    f"classifier={classifier_intent.value}",
                    f"deterministic_override={det.value}",
                ],
            )

        # Múltiplos sinais conflitantes
        return OperationResolution(
            message_intent=classifier_intent,
            resolved_operation_type=None,
            status=OperationResolutionStatus.AMBIGUOUS,
            source=OperationSource.DETERMINISTIC_SIGNAL,
            evidence=[
                f"conflicting_signals={[s.value for s in deterministic_signals]}"
            ],
        )

    def _has_change_verb(self, msg_lower: str) -> bool:
        return any(re.search(p, msg_lower) for p in self.CHANGE_VERBS)

    def _has_quantity_evidence(self, msg_lower: str) -> bool:
        # dígito (com ou sem decimal) — sem \b para casar com "5kg"
        if re.search(r"\d+(?:[.,]\d+)?", msg_lower):
            return True
        # palavra numérica
        for w in self.NUMBER_WORDS:
            if re.search(r"\b" + w + r"\b", msg_lower):
                return True
        return False