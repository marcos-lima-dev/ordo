import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from order.catalog_retriever import CatalogRetriever
from order.product_resolver import ProductResolver


@pytest.fixture
def retriever():
    return CatalogRetriever()


@pytest.fixture
def resolver():
    return ProductResolver()


# =============================================
# CR-01: EMPTY QUERY → EMPTY CANDIDATES
# =============================================

@pytest.mark.parametrize("message", [
    "adiciona 3",
    "coloca 2",
    "quero 5",
    "manda 10kg",
    "tira uma",
    "muda para 4",
])
def test_no_product_fabrication(retriever, message):
    """CR-01: mensagens sem evidência lexical de produto
    NÃO devem produzir candidatos arbitrários."""
    result = retriever.retrieve(message)
    forbidden = {"CQ-20", "CQ-08", "CQ-09", "CQ-10"}
    assert not (set(result) & forbidden), (
        f"Retriever fabricou produto para '{message}': {result}"
    )


def test_empty_message_returns_empty(retriever):
    assert retriever.retrieve("") == []


# =============================================
# CR-02: NO EVIDENCE → NO PRODUCT
# =============================================

def test_resolver_no_exact_match_without_evidence(resolver):
    """CR-02: candidato único sem evidência positiva não autoriza EXACT_MATCH."""
    try:
        status = resolver.resolve(["CQ-20"], product_term=None, brand=None, evidence=None)
    except TypeError:
        pytest.fail("ProductResolver não suporta verificação de evidência (CR-02 violado)")

    assert status != "EXACT_MATCH", (
        f"ProductResolver autorizou EXACT_MATCH sem evidência positiva: {status}"
    )


# =============================================
# CR-03: PRODUTO EXPLÍCITO NÃO É APAGADO POR RUÍDO
# =============================================

@pytest.mark.parametrize("message,expected_sku", [
    ("quero 2kg de queijo prato", "CQ-74"),
    ("me manda 5kg de mussarela", "CQ-30"),
    ("quero 10kg daquela manteiga sem sal", None),
])
def test_product_evidence_survives_noise(retriever, message, expected_sku):
    """CR-03: informação comercial relevante sobrevive ao ruído."""
    result = retriever.retrieve(message)
    assert len(result) > 0, f"Produto desapareceu para '{message}'"
    if expected_sku:
        assert expected_sku in result, f"{expected_sku} não encontrado: {result}"


# =============================================
# AMBIGUIDADE PRESERVADA
# =============================================

@pytest.mark.parametrize("message", [
    "quero provolone",
    "manda gorgonzola",
    "quero manteiga",
    "coloca queijo",
])
def test_generic_term_remains_ambiguous(retriever, message):
    """Termos genéricos/família não devem virar match único."""
    result = retriever.retrieve(message)
    assert len(result) != 1, (
        f"Termo genérico '{message}' virou match único: {result}"
    )


# =============================================
# R1 — CONSTRAINTS COM PROVENIÊNCIA
# =============================================

def test_presentation_constraint_feta_forma(retriever):
    """Caso real: 'feta forma' + presentation='forma' reduz a CQ-54."""
    candidates, prov = retriever.retrieve_with_provenance(
        "feta forma", presentation="forma"
    )
    assert candidates == ["CQ-54"], f"Esperado ['CQ-54'], obtido {candidates}"
    assert "CQ-54" in prov


def test_presentation_constraint_parmesao_forma(retriever):
    """Caso real: 'parmesão curado forma' + presentation='forma' reduz a CQ-43."""
    candidates, prov = retriever.retrieve_with_provenance(
        "parmesão curado forma", presentation="forma"
    )
    assert candidates == ["CQ-43"], f"Esperado ['CQ-43'], obtido {candidates}"


def test_presentation_constraint_brie_forma_no_leak(retriever):
    """Caso real: 'brie forma' + presentation='forma' remove CQ-02 (triângulo)."""
    candidates, prov = retriever.retrieve_with_provenance(
        "brie forma", presentation="forma"
    )
    assert "CQ-02" not in candidates, f"CQ-02 vazou: {candidates}"
    assert set(candidates) == {"CQ-01", "CQ-03"}, f"Obtido: {candidates}"


def test_brand_constraint_provolone_tania(retriever):
    """Caso real: 'provolone' + brand='Tânia' reduz a CQ-44."""
    candidates, prov = retriever.retrieve_with_provenance(
        "provolone", brand="Tânia"
    )
    assert candidates == ["CQ-44"], f"Esperado ['CQ-44'], obtido {candidates}"
    assert "CQ-44" in prov


def test_constraints_preserve_provenance(retriever):
    """Filtro de constraint NÃO apaga proveniência dos sobreviventes."""
    candidates, prov = retriever.retrieve_with_provenance(
        "feta forma", presentation="forma"
    )
    for cid in candidates:
        assert cid in prov, f"Candidato {cid} sem proveniência"


# =============================================
# R2 — TAXONOMIA DE EVIDÊNCIA (autorização vs retrieval)
# =============================================

def test_unique_alias_exact_authorizes_exact_match(resolver):
    status = resolver.resolve(
        ["CQ-30"], evidence={"CQ-30": "ORIGINAL_ALIAS_EXACT"}
    )
    assert status == "EXACT_MATCH", f"Esperado EXACT_MATCH, obtido {status}"


def test_unique_name_exact_authorizes_exact_match(resolver):
    status = resolver.resolve(
        ["CQ-30"], evidence={"CQ-30": "NORMALIZED_NAME_EXACT"}
    )
    assert status == "EXACT_MATCH"


def test_unique_original_exact_authorizes_exact_match(resolver):
    status = resolver.resolve(
        ["CQ-X"], evidence={"CQ-X": "ORIGINAL_ORIGINAL_EXACT"}
    )
    assert status == "EXACT_MATCH"


def test_unique_alias_token_does_not_authorize_exact_match(resolver):
    status = resolver.resolve(
        ["CQ-44"], evidence={"CQ-44": "ORIGINAL_ALIAS_TOKEN"}
    )
    assert status == "AMBIGUOUS", f"Esperado AMBIGUOUS, obtido {status}"


def test_unique_name_token_does_not_authorize_exact_match(resolver):
    status = resolver.resolve(
        ["CQ-X"], evidence={"CQ-X": "ORIGINAL_NAME_TOKEN"}
    )
    assert status == "AMBIGUOUS"


def test_unique_alias_subset_does_not_authorize_exact_match(resolver):
    status = resolver.resolve(
        ["CQ-46"], evidence={"CQ-46": "ORIGINAL_ALIAS_SUBSET"}
    )
    assert status == "AMBIGUOUS"


def test_unique_name_subset_does_not_authorize_exact_match(resolver):
    status = resolver.resolve(
        ["CQ-30"], evidence={"CQ-30": "ORIGINAL_NAME_SUBSET"}
    )
    assert status == "AMBIGUOUS"


def test_unique_fuzzy_does_not_authorize_exact_match(resolver):
    status = resolver.resolve(
        ["CQ-44"], evidence={"CQ-44": "ORIGINAL_ALIAS_FUZZY"}
    )
    assert status == "AMBIGUOUS"


def test_evidence_none_does_not_authorize_exact_match(resolver):
    status = resolver.resolve(["CQ-30"], evidence=None)
    assert status == "AMBIGUOUS"


# =============================================
# R1 — DETERMINISMO
# =============================================

def test_retrieve_with_provenance_is_deterministic(retriever):
    """Ordem de candidatos deve ser estável entre execuções."""
    msg = "brie forma"
    baseline, _ = retriever.retrieve_with_provenance(msg, presentation="forma")
    for _ in range(5):
        run_n, _ = retriever.retrieve_with_provenance(msg, presentation="forma")
        assert run_n == baseline, f"Ordem não determinística: {run_n} != {baseline}"