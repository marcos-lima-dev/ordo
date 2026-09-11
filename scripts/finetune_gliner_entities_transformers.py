import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from transformers import AutoTokenizer, AutoModelForTokenClassification, TrainingArguments, Trainer
from transformers import DataCollatorForTokenClassification
from datasets import Dataset
import numpy as np
from seqeval.metrics import accuracy_score

# Labels BIO
LABEL_MAP = {
    "O": 0,
    "B-PRODUCT": 1,
    "I-PRODUCT": 2,
    "B-BRAND": 3,
    "I-BRAND": 4,
    "B-PRESENTATION": 5,
    "I-PRESENTATION": 6,
}
ID_TO_LABEL = {v: k for k, v in LABEL_MAP.items()}

def load_entity_dataset(path):
    data = []
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            text = item["text"]
            entities = item["entities"]
            tokens = text.split()
            labels = ["O"] * len(tokens)
            
            for ent in entities:
                ent_text = ent["text"]
                label = ent["label"]
                start = text.find(ent_text)
                if start == -1:
                    continue
                token_start = len(text[:start].split())
                token_end = len(text[:start+len(ent_text)].split())
                for i in range(token_start, token_end):
                    if i == token_start:
                        labels[i] = f"B-{label}"
                    else:
                        labels[i] = f"I-{label}"
            
            label_ids = [LABEL_MAP.get(l, 0) for l in labels]
            data.append({"tokens": tokens, "labels": label_ids})
    return data

def tokenize_and_align_labels(examples, tokenizer):
    tokenized_inputs = tokenizer(
        examples["tokens"],
        truncation=True,
        is_split_into_words=True,
        padding="max_length",
        max_length=128,
    )
    labels = []
    for i, label in enumerate(examples["labels"]):
        word_ids = tokenized_inputs.word_ids(batch_index=i)
        previous_word_idx = None
        label_ids = []
        for word_idx in word_ids:
            if word_idx is None:
                label_ids.append(-100)
            elif word_idx != previous_word_idx:
                label_ids.append(label[word_idx])
            else:
                label_ids.append(-100)
            previous_word_idx = word_idx
        labels.append(label_ids)
    tokenized_inputs["labels"] = labels
    return tokenized_inputs

def compute_metrics(p):
    predictions, labels = p
    predictions = np.argmax(predictions, axis=2)
    true_predictions = [
        [ID_TO_LABEL[p] for (p, l) in zip(pred, lab) if l != -100]
        for pred, lab in zip(predictions, labels)
    ]
    true_labels = [
        [ID_TO_LABEL[l] for (p, l) in zip(pred, lab) if l != -100]
        for pred, lab in zip(predictions, labels)
    ]
    flat_pred = [p for pred in true_predictions for p in pred if p != 'O']
    flat_true = [l for lab in true_labels for l in lab if l != 'O']
    return {"accuracy": accuracy_score(flat_true, flat_pred) if flat_true else 0.0}

def main():
    print("Carregando datasets...")
    train_data = load_entity_dataset("datasets/entities/train.jsonl")
    val_data = load_entity_dataset("datasets/entities/val.jsonl")
    print(f"Train: {len(train_data)}, Val: {len(val_data)}")

    train_dataset = Dataset.from_list(train_data)
    val_dataset = Dataset.from_list(val_data)

    # Usamos o tokenizer do GLiNER (Bert)
    model_name = "urchade/gliner_medium"
    tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
    model = AutoModelForTokenClassification.from_pretrained(
        model_name,
        num_labels=len(LABEL_MAP),
        id2label=ID_TO_LABEL,
        label2id=LABEL_MAP,
    )

    train_dataset = train_dataset.map(
        lambda x: tokenize_and_align_labels(x, tokenizer),
        batched=True,
    )
    val_dataset = val_dataset.map(
        lambda x: tokenize_and_align_labels(x, tokenizer),
        batched=True,
    )

    data_collator = DataCollatorForTokenClassification(tokenizer=tokenizer)

    training_args = TrainingArguments(
        output_dir="./models/gliner_entities_finetuned",
        num_train_epochs=10,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        warmup_steps=10,
        weight_decay=0.01,
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
    )

    print("Iniciando fine-tuning...")
    trainer.train()

    model.save_pretrained("./models/gliner_entities_finetuned")
    tokenizer.save_pretrained("./models/gliner_entities_finetuned")
    print("Modelo salvo em ./models/gliner_entities_finetuned")

if __name__ == "__main__":
    main()