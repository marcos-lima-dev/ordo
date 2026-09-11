import json
from difflib import SequenceMatcher

def load_golden_messages():
    with open("tests/golden_dataset.jsonl") as f:
        return [json.loads(line)["input"] for line in f if line.strip()]

def load_train_messages():
    with open("datasets/gliner_train.jsonl") as f:
        return [json.loads(line)["text"] for line in f if line.strip()]

def similar(a, b, threshold=0.8):
    return SequenceMatcher(None, a, b).ratio() >= threshold

golden = load_golden_messages()
train = load_train_messages()

overlaps = []
for g in golden:
    for t in train:
        if g == t:
            overlaps.append(f"Exato: '{g}' == '{t}'")
        elif similar(g, t):
            overlaps.append(f"Paráfrase: '{g}' ≈ '{t}'")

if overlaps:
    print("⚠️ Possível overlap ou paráfrase muito próxima:")
    for o in overlaps[:10]:
        print("  ", o)
else:
    print("✅ Nenhum overlap ou paráfrase evidente encontrada.")