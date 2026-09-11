from .base import CandidateAdapter, ADAPTER_REGISTRY

# Importar todos os adaptadores para que sejam registrados
from .perfect_mock import PerfectMockAdapter
from .broken_mock import BrokenMockAdapter
from .deterministic import DeterministicAdapter
from .tucano import TucanoAdapter
from .nuextract import NuExtractAdapter
from .gliner_adapter import GLiNERAdapter
from .modular import ModularAdapter  # <-- ADICIONAR

__all__ = [
    "CandidateAdapter",
    "ADAPTER_REGISTRY",
    "PerfectMockAdapter",
    "BrokenMockAdapter",
    "DeterministicAdapter",
    "TucanoAdapter",
    "NuExtractAdapter",
    "GLiNERAdapter",
    "ModularAdapter",  # <-- ADICIONAR
]