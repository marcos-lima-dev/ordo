import json
from pathlib import Path

# Mapeamento de intenções para labels numéricas
INTENT_MAP = {
    "ADD_ITEM": 0,
    "REMOVE_ITEM": 1,
    "CHANGE_QUANTITY": 2,
    "CONFIRM_ORDER": 3,
    "CANCEL_ORDER": 4,
    "UNKNOWN": 5,
}
ID_TO_INTENT = {v: k for k, v in INTENT_MAP.items()}

def load_intent_dataset(input_path, output_path):
    data = []
    with open(input_path) as f:
        for line in f:
            item = json.loads(line)
            text = item["text"]
            intent = item["labels"]["intent"]
            label = INTENT_MAP.get(intent, 5)  # UNKNOWN
            data.append({"text": text, "label": label})
    
    with open(output_path, "w") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Salvo {len(data)} exemplos em {output_path}")

def main():
    Path("datasets/intent").mkdir(parents=True, exist_ok=True)
    load_intent_dataset("datasets/gliner_train.jsonl", "datasets/intent/train.jsonl")
    load_intent_dataset("datasets/gliner_val.jsonl", "datasets/intent/val.jsonl")
    load_intent_dataset("datasets/gliner_holdout.jsonl", "datasets/intent/holdout.jsonl")

if __name__ == "__main__":
    main()