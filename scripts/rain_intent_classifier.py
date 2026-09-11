import json
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer
from datasets import Dataset
from sklearn.metrics import accuracy_score
import numpy as np

# Carrega dados
def load_intent_data(path):
    X, y = [], []
    with open(path) as f:
        for line in f:
            item = json.loads(line)
            X.append(item["text"])
            y.append(item["labels"]["intent"])
    return X, y

# Mapeia intenções para IDs
intent_map = {
    "ADD_ITEM": 0,
    "REMOVE_ITEM": 1,
    "CHANGE_QUANTITY": 2,
    "CONFIRM_ORDER": 3,
    "CANCEL_ORDER": 4,
    "UNKNOWN": 5
}
id_to_intent = {v: k for k, v in intent_map.items()}

def tokenize_function(examples, tokenizer):
    return tokenizer(examples["text"], padding="max_length", truncation=True, max_length=128)

def compute_metrics(p):
    preds = np.argmax(p.predictions, axis=1)
    return {"accuracy": accuracy_score(p.label_ids, preds)}

def main():
    print("Carregando dados...")
    train_texts, train_labels = load_intent_data("datasets/gliner_train.jsonl")
    val_texts, val_labels = load_intent_data("datasets/gliner_val.jsonl")
    
    print(f"Train: {len(train_texts)}, Val: {len(val_texts)}")
    
    train_dataset = Dataset.from_dict({"text": train_texts, "label": [intent_map[l] for l in train_labels]})
    val_dataset = Dataset.from_dict({"text": val_texts, "label": [intent_map[l] for l in val_labels]})
    
    # Carrega modelo
    model_name = "distilbert-base-portuguese-cased"
    print(f"Carregando modelo {model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=len(intent_map)
    )
    
    # Tokeniza
    train_dataset = train_dataset.map(lambda x: tokenize_function(x, tokenizer), batched=True)
    val_dataset = val_dataset.map(lambda x: tokenize_function(x, tokenizer), batched=True)
    
    # Treina
    training_args = TrainingArguments(
        output_dir="./models/intent_classifier",
        num_train_epochs=15,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        warmup_steps=5,
        weight_decay=0.01,
        logging_steps=5,
        evaluation_strategy="epoch",
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
        compute_metrics=compute_metrics,
    )
    
    print("Iniciando treinamento...")
    trainer.train()
    
    # Salva modelo
    model.save_pretrained("./models/intent_classifier")
    tokenizer.save_pretrained("./models/intent_classifier")
    print("Classificador salvo em ./models/intent_classifier")

if __name__ == "__main__":
    main()