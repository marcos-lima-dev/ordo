import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from order.catalog_retriever import CatalogRetriever

def load_benchmark():
    path = Path("datasets/catalog_retrieval_benchmark.jsonl")
    cases = []
    with open(path) as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))
    return cases

def evaluate(retriever, cases):
    results = []
    recall_at_1 = 0
    recall_at_3 = 0
    recall_at_5 = 0
    total = len(cases)
    
    for case in cases:
        query = case["message"]
        expected = set(case["expected_candidates"])
        status = case["expected_status"]
        
        retrieved = retriever.retrieve(query)
        retrieved_set = set(retrieved)
        
        # Recall@k
        if expected.issubset(retrieved_set):
            recall_at_1 += 1
            recall_at_3 += 1
            recall_at_5 += 1
        elif any(e in retrieved_set for e in expected):
            recall_at_3 += 1
            recall_at_5 += 1
        
        # Verifica se o status de ambiguidade foi preservado
        is_ambiguous = (len(retrieved) > 1)
        expected_ambiguous = (status == "AMBIGUOUS")
        ambiguity_ok = (is_ambiguous == expected_ambiguous)
        
        results.append({
            "query": query,
            "expected": list(expected),
            "retrieved": retrieved,
            "expected_status": status,
            "is_ambiguous": is_ambiguous,
            "ambiguity_ok": ambiguity_ok,
            "recall_ok": expected.issubset(retrieved_set)
        })
    
    return {
        "recall_at_1": recall_at_1 / total,
        "recall_at_3": recall_at_3 / total,
        "recall_at_5": recall_at_5 / total,
        "total": total,
        "details": results
    }

def main():
    cases = load_benchmark()
    print(f"Carregados {len(cases)} casos")
    
    retriever = CatalogRetriever()
    metrics = evaluate(retriever, cases)
    
    print("\n=== CATALOG RETRIEVAL BENCHMARK ===")
    print(f"Total: {metrics['total']}")
    print(f"Recall@1: {metrics['recall_at_1']:.2%}")
    print(f"Recall@3: {metrics['recall_at_3']:.2%}")
    print(f"Recall@5: {metrics['recall_at_5']:.2%}")
    
    # Conta casos onde a ambiguidade foi preservada
    ambiguity_ok = sum(1 for r in metrics['details'] if r['ambiguity_ok'])
    print(f"Ambiguity correct: {ambiguity_ok}/{metrics['total']} ({ambiguity_ok/metrics['total']:.2%})")
    
    # Casos onde o recall falhou (SKU correto não foi recuperado)
    recall_failures = [r for r in metrics['details'] if not r['recall_ok']]
    if recall_failures:
        print(f"\n⚠️ Recall failures ({len(recall_failures)}):")
        for r in recall_failures[:5]:
            print(f"  Query: '{r['query']}'")
            print(f"    Expected: {r['expected']}")
            print(f"    Retrieved: {r['retrieved']}")
    
    # Salva relatório
    output_path = Path("reports/catalog_benchmark.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    print(f"\nRelatório salvo em {output_path}")

if __name__ == "__main__":
    main()