import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from order.catalog_retriever import CatalogRetriever

def test_basic_retrieval():
    retriever = CatalogRetriever()
    cases = [
        ("provolone", ["CQ-44", "CQ-46"]),
        ("manteiga sem sal", ["CQ-29"]),
        ("brie", ["CQ-01", "CQ-02", "CQ-03"]),
        ("catupiry bisnaga", ["CQ-62", "CQ-63"]),
    ]
    for query, expected in cases:
        result = retriever.retrieve(query)
        print(f"Query: '{query}' → {result}")
        # Verifica se todos os esperados estão nos resultados
        assert all(e in result for e in expected)

def test_retrieval_with_constraints():
    retriever = CatalogRetriever()
    result = retriever.retrieve_with_constraints("provolone", brand="Tânia")
    assert "CQ-44" in result
    assert "CQ-46" not in result  # Riqueza de Minas

def test_retrieval_with_presentation():
    retriever = CatalogRetriever()
    result = retriever.retrieve_with_constraints("emmental", presentation="forma")
    assert "CQ-08" in result or "CQ-10" in result
    # "CQ-09" é barra, não deve aparecer

if __name__ == "__main__":
    test_basic_retrieval()
    test_retrieval_with_constraints()
    test_retrieval_with_presentation()
    print("Todos os testes do CatalogRetriever passaram!")