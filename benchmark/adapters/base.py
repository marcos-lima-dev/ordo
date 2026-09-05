from abc import ABC, abstractmethod

class CandidateAdapter(ABC):
    """Interface padrão para qualquer candidato avaliado."""

    @abstractmethod
    def predict(self, message: str) -> dict:
        """
        Recebe uma mensagem do cliente e retorna a predição no formato
        definido pelo JSON Schema do contrato.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome do candidato para identificação no relatório."""
        pass