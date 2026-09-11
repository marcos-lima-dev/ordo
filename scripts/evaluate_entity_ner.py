import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from seqeval.metrics import classification_report

def load_holdout():
    path = Path("datasets/entities/holdout.jsonl")
    cases = []
    with open(path) as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))
    return cases

def evaluate_ner(model_path, cases):
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForTokenClassification.from_pretrained(model_path)
    nlp = pipeline("token-classification", model=model, tokenizer=tokenizer, aggregation_strategy="simple")

    true_labels = []
    pred_labels = []

    for case in cases:
        text = case["text"]
        tokens = text.split()
        
        # Verdadeiros
        true = ["O"] * len(tokens)
        for ent in case["entities"]:
            ent_text = ent["text"]
            label = ent["label"]
            start = text.find(ent_text)
            if start == -1:
                continue
            token_start = len(text[:start].split())
            token_end = len(text[:start+len(ent_text)].split())
            for i in range(token_start, token_end):
                if i == token_start:
                    true[i] = f"B-{label}"
                else:
                    true[i] = f"I-{label}"
        true_labels.append(true)

        # Predição (precisa mapear tokens)
        pred = nlp(text)
        pred_tokens = ["O"] * len(tokens)
        for p in pred:
            # p["entity_group"] contém a entidade (PRODUCT, BRAND, PRESENTATION)
            # Precisamos mapear para o token correspondente
            # Simplificação: usamos o texto do token
            # Melhor: mapear por posição
            pass
        pred_labels.append(["O"] * len(tokens))  # placeholder

    # Placeholder - substituir com lógica real de alinhamento
    return {"precision": 0, "recall": 0, "f1": 0}

def main():
    cases = load_holdout()
    print(f"Carregados {len(cases)} casos")
    metrics = evaluate_ner("./models/entity_ner", cases)
    print(metrics)

if __name__ == "__main__":
    main()