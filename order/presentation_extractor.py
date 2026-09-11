# order/presentation_extractor.py
from typing import Optional

PRESENTATION_TERMS = {
    "forma", "formas",
    "barra", "barras",
    "bloco", "blocos",
    "bisnaga", "bisnagas",
    "peça", "peças",
    "pote", "potes",
    "saco", "sacos",
    "garrafa", "garrafas",
    "caixa", "caixas",
    "balde", "baldes",
    "pacote", "pacotes",
    "fração", "vácuo",
    "unidade", "unidades",
    "triângulo",
    "cartela", "cartelas",
    "meia forma", "1/2 forma",
    "1/8",
}


def extract_presentation(message: str) -> Optional[str]:
    """
    Extrai o termo de apresentação da mensagem usando dicionário determinístico.
    Retorna o termo encontrado ou None.
    """
    msg_lower = message.lower()
    # Ordena por tamanho para pegar "meia forma" antes de "forma"
    for term in sorted(PRESENTATION_TERMS, key=len, reverse=True):
        if term in msg_lower:
            return term
    return None