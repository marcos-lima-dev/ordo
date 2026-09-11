from abc import ABC, abstractmethod

# Dicionário global de registro de adaptadores
ADAPTER_REGISTRY = {}

def register_adapter(name):
    """
    Decorator para registrar adaptadores automaticamente.
    Uso:
        @register_adapter("meu_modelo")
        class MeuModeloAdapter(CandidateAdapter):
            ...
    """
    def decorator(cls):
        ADAPTER_REGISTRY[name] = cls
        return cls
    return decorator

class CandidateAdapter(ABC):
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