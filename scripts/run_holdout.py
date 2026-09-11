import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from collections import defaultdict
from benchmark.adapters import ModularAdapter
from benchmark.evaluator import Evaluator

def load_holdout_messages():
    path = Path("datasets/holdout_messages.jsonl")
    cases = []
    with open(path) as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))
    return cases

def main():
    print("Carregando holdout messages...")
    cases = load_holdout_messages()
    print(f"Total: {len(cases)} mensagens")

    adapter = ModularAdapter()
    evaluator = Evaluator()

    results = []
    intent_correct = 0
    intent_total = 0
    intent_confusion = defaultdict(lambda: defaultdict(int))

    for case in cases:
        msg = case["text"]
        expected = case["expected"]
        pred = adapter.predict(msg)

        # Avalia intent
        pred_intent = pred.get("intent")
        exp_intent = expected.get("intent")
        intent_total += 1
        if pred_intent == exp_intent:
            intent_correct += 1
        intent_confusion[exp_intent][pred_intent] += 1

        # Avaliação completa (opcional)
        eval_result = evaluator.evaluate(expected, pred)

        results.append({
            "message": msg,
            "expected": expected,
            "prediction": pred,
            "evaluation": eval_result
        })

    print(f"\nIntent Accuracy: {intent_correct}/{intent_total} ({intent_correct/intent_total*100:.1f}%)")
    print("\nMatriz de Confusão (Intents):")
    print("Expected → Predicted")
    for exp, preds in sorted(intent_confusion.items()):
        print(f"  {exp}:")
        for pred, count in sorted(preds.items()):
            print(f"    → {pred}: {count}")

    # Salva relatório detalhado
    output_path = Path("reports/holdout_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "total": intent_total,
            "correct": intent_correct,
            "accuracy": intent_correct/intent_total if intent_total else 0,
            "confusion_matrix": {k: dict(v) for k, v in intent_confusion.items()},
            "cases": results
        }, f, indent=2, ensure_ascii=False)
    print(f"\nRelatório salvo em {output_path}")

if __name__ == "__main__":
    main()