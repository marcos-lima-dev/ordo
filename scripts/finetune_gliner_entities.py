import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from gliner import GLiNER
from gliner.training import Trainer, TrainingArguments
from gliner.data_processor import DataProcessor

def load_entity_dataset(path):
    data = []
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            text = item["text"]
            entities = []
            for ent in item["entities"]:
                start = ent["start"]
                end = ent["end"]
                label = ent["label"]
                entities.append((start, end, label))
            data.append({"text": text, "entities": entities})
    return data

def main():
    print("Carregando datasets...")
    train_data = load_entity_dataset("datasets/entities/train.jsonl")
    val_data = load_entity_dataset("datasets/entities/val.jsonl")
    print(f"Train: {len(train_data)}, Val: {len(val_data)}")

    print("Carregando modelo base GLiNER...")
    model = GLiNER.from_pretrained("urchade/gliner_medium")

    labels = ["PRODUCT", "BRAND", "PRESENTATION"]
    
    # DataProcessor
    processor = DataProcessor()
    train_dataset = processor(train_data, labels, tokenizer=model.tokenizer)
    val_dataset = processor(val_data, labels, tokenizer=model.tokenizer)

    training_args = TrainingArguments(
        output_dir="./models/gliner_entities_finetuned",
        num_train_epochs=10,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        warmup_steps=10,
        weight_decay=0.01,
        logging_steps=10,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_processor=processor,
        tokenizer=model.tokenizer,
    )

    print("Iniciando fine-tuning...")
    trainer.train()

    model.save_pretrained("./models/gliner_entities_finetuned")
    print("Modelo salvo em ./models/gliner_entities_finetuned")

if __name__ == "__main__":
    main()