import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from gliner import GLiNER
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from collections import defaultdict

def load_holdout():
    path = Path("datasets/entities/holdout.jsonl")
    cases = []
    with open(path) as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))
    return cases

def evaluate_gliner(model, cases):
    labels = ["PRODUCT", "BRAND", "PRESENTATION"]
    total = defaultdict(int)
    correct = defaultdict(int)
    predicted = defaultdict(int)

    for case in cases:
        text = case["text"]
        expected = case["entities"]
        expected_by_label = defaultdict(list)
        for ent in expected:
            expected_by_label[ent["label"]].append(ent["text"].lower())

        preds = model.predict_entities(text, labels, threshold=0.3)
        pred_by_label = defaultdict(list)
        for p in preds:
            pred_by_label[p["label"]].append(p["text"].lower())

        for label in labels:
            exp_set = set(expected_by_label.get(label, []))
            pred_set = set(pred_by_label.get(label, []))
            total[label] += len(exp_set)
            correct[label] += len(exp_set & pred_set)
            predicted[label] += len(pred_set)

    metrics = {}
    for label in labels:
        p = correct[label] / predicted[label] if predicted[label] > 0 else 0
        r = correct[label] / total[label] if total[label] > 0 else 0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0
        metrics[label] = {"precision": p, "recall": r, "f1": f1}
    return metrics

def evaluate_bert_ner(model_path, cases):
    # Usa pipeline do transformers para NER com BERT
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForTokenClassification.from_pretrained(model_path)
    nlp = pipeline("token-classification", model=model, tokenizer=tokenizer, aggregation_strategy="simple")

    total = defaultdict(int)
    correct = defaultdict(int)
    predicted = defaultdict(int)

    for case in cases:
        text = case["text"]
        expected = case["entities"]
        expected_by_label = defaultdict(list)
        for ent in expected:
            expected_by_label[ent["label"]].append(ent["text"].lower())

        preds = nlp(text)
        pred_by_label = defaultdict(list)
        for p in preds:
            label = p["entity_group"]
            if label in ["PRODUCT", "BRAND", "PRESENTATION"]:
                pred_by_label[label].append(p["word"].lower())

        for label in ["PRODUCT", "BRAND", "PRESENTATION"]:
            exp_set = set(expected_by_label.get(label, []))
            pred_set = set(pred_by_label.get(label, []))
            total[label] += len(exp_set)
            correct[label] += len(exp_set & pred_set)
            predicted[label] += len(pred_set)

    metrics = {}
    for label in ["PRODUCT", "BRAND", "PRESENTATION"]:
        p = correct[label] / predicted[label] if predicted[label] > 0 else 0
        r = correct[label] / total[label] if total[label] > 0 else 0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0
        metrics[label] = {"precision": p, "recall": r, "f1": f1}
    return metrics

def main():
    cases = load_holdout()
    print(f"Carregados {len(cases)} casos no holdout de entidades.")

    # 1. GLiNER base (sem fine-tuning)
    print("\n=== GLiNER BASE ===")
    model_base = GLiNER.from_pretrained("urchade/gliner_medium")
    metrics_base = evaluate_gliner(model_base, cases)
    for label, m in metrics_base.items():
        print(f"  {label}: P={m['precision']:.3f}, R={m['recall']:.3f}, F1={m['f1']:.3f}")

    # 2. BERT NER fine-tuned
    print("\n=== BERT NER FINE-TUNED ===")
    try:
        metrics_bert = evaluate_bert_ner("./models/entity_ner", cases)
        for label, m in metrics_bert.items():
            print(f"  {label}: P={m['precision']:.3f}, R={m['recall']:.3f}, F1={m['f1']:.3f}")
    except Exception as e:
        print(f"Erro ao carregar modelo BERT NER: {e}")

if __name__ == "__main__":
    main()