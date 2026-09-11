from enum import Enum
from typing import List, Optional

class ResolutionStatus:
    EXACT_MATCH = "EXACT_MATCH"
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_FOUND = "NOT_FOUND"

class ProductResolver:
    def resolve(self, candidates: List[str], product_term: Optional[str] = None, brand: Optional[str] = None) -> str:
        """
        Determina o status de resolução com base nos candidatos retornados.
        """
        if not candidates:
            return ResolutionStatus.NOT_FOUND
        
        if len(candidates) == 1:
            return ResolutionStatus.EXACT_MATCH
        
        # Se houver múltiplos candidatos, verifica se podemos reduzir com restrições
        # Por enquanto, retorna AMBIGUOUS
        return ResolutionStatus.AMBIGUOUS
    
    def is_resolved(self, status: str) -> bool:
        return status in [ResolutionStatus.EXACT_MATCH, ResolutionStatus.HIGH_CONFIDENCE]