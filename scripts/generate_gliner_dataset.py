import json
import random
from pathlib import Path

# Dicionário de variações
VARIACOES = {
    "quero": ["quero", "me manda", "coloca", "bota", "manda", "gostaria de", "queria"],
    "kg": ["kg", "quilos", "quilo", "k", "kg"],
    "provolone": ["provolone", "provolne", "provole", "provolone"],
    "manteiga": ["manteiga", "mantega", "manteiga", "manteiga sem sal"],
    "Catupiry": ["Catupiry", "catupiry", "catupiri"],
    "Tânia": ["Tânia", "Tania", "tânia"],
    "Coyote": ["Coyote", "coyote"],
    "São Vicente": ["São Vicente", "Sao Vicente", "S.Vicente"],
}

# Casos base
CASOS_BASE = [
    {
        "text": "quero 5kg de provolone",
        "intent": "ADD_ITEM",
        "entities": [{"label": "produto", "text": "provolone"}]
    },
    {
        "text": "quero 10 quilos da manteiga sem sal",
        "intent": "ADD_ITEM",
        "entities": [{"label": "produto", "text": "manteiga sem sal"}]
    },
    {
        "text": "quero 6 bisnagas de Catupiry",
        "intent": "ADD_ITEM",
        "entities": [
            {"label": "produto", "text": "Catupiry"},
            {"label": "apresentacao", "text": "bisnagas"}
        ]
    },
    {
        "text": "coloca 3 provolones",
        "intent": "ADD_ITEM",
        "entities": [{"label": "produto", "text": "provolones"}]
    },
    {
        "text": "manda cinco kg daquele provolone",
        "intent": "ADD_ITEM",
        "entities": [{"label": "produto", "text": "provolone"}]
    },
    {
        "text": "quero o provolone da Tânia",
        "intent": "ADD_ITEM",
        "entities": [
            {"label": "produto", "text": "provolone"},
            {"label": "marca", "text": "Tânia"}
        ]
    },
    {
        "text": "manda duas formas daquele provolone",
        "intent": "ADD_ITEM",
        "entities": [
            {"label": "produto", "text": "provolone"},
            {"label": "apresentacao", "text": "formas"}
        ]
    },
    {
        "text": "me manda duas manteigas",
        "intent": "ADD_ITEM",
        "entities": [{"label": "produto", "text": "manteigas"}]
    },
    {
        "text": "tira o provolone",
        "intent": "REMOVE_ITEM",
        "entities": [{"label": "produto", "text": "provolone"}]
    },
    {
        "text": "pode fechar",
        "intent": "CONFIRM_ORDER",
        "entities": []
    },
    {
        "text": "cancela tudo",
        "intent": "CANCEL_ORDER",
        "entities": []
    },
    {
        "text": "na verdade são 8kg de manteiga",
        "intent": "CHANGE_QUANTITY",
        "entities": [{"label": "produto", "text": "manteiga"}]
    },
    {
        "text": "quero 2 kg de gorgonzola",
        "intent": "ADD_ITEM",
        "entities": [{"label": "produto", "text": "gorgonzola"}]
    },
    {
        "text": "brie 1kg",
        "intent": "ADD_ITEM",
        "entities": [{"label": "produto", "text": "brie"}]
    },
    {
        "text": "requeijão",
        "intent": "ADD_ITEM",
        "entities": [{"label": "produto", "text": "requeijão"}]
    },
    {
        "text": "coloca 4 potes de burrata",
        "intent": "ADD_ITEM",
        "entities": [
            {"label": "produto", "text": "burrata"},
            {"label": "apresentacao", "text": "potes"}
        ]
    },
    {
        "text": "quero dois provolones da Tânia",
        "intent": "ADD_ITEM",
        "entities": [
            {"label": "produto", "text": "provolones"},
            {"label": "marca", "text": "Tânia"}
        ]
    },
    {
        "text": "me vê cinco quilos de provolone",
        "intent": "ADD_ITEM",
        "entities": [{"label": "produto", "text": "provolone"}]
    },
    {
        "text": "bota 5 kg provolone",
        "intent": "ADD_ITEM",
        "entities": [{"label": "produto", "text": "provolone"}]
    },
    {
        "text": "5k provolone",
        "intent": "ADD_ITEM",
        "entities": [{"label": "produto", "text": "provolone"}]
    },
]

def gerar_variacao(texto, intent, entities):
    """Gera variações de um caso base."""
    variacoes = []
    for _ in range(3):  # 3 variações por caso
        novo_texto = texto
        # Substitui palavras por variações
        for palavra, opcoes in VARIACOES.items():
            if palavra in novo_texto:
                novo_texto = novo_texto.replace(palavra, random.choice(opcoes))
        # Rotaciona ordem das palavras (simples)
        if random.random() < 0.2:
            palavras = novo_texto.split()
            if len(palavras) > 2:
                idx = random.randint(0, len(palavras)-2)
                palavras[idx], palavras[idx+1] = palavras[idx+1], palavras[idx]
                novo_texto = " ".join(palavras)
        variacoes.append({
            "text": novo_texto,
            "intent": intent,
            "entities": entities
        })
    return variacoes

def main():
    dataset = []
    
    # Adiciona casos base
    for caso in CASOS_BASE:
        dataset.append({
            "text": caso["text"],
            "labels": {
                "intent": caso["intent"],
                "entities": caso["entities"]
            }
        })
        
        # Adiciona variações
        for variacao in gerar_variacao(caso["text"], caso["intent"], caso["entities"]):
            dataset.append({
                "text": variacao["text"],
                "labels": {
                    "intent": variacao["intent"],
                    "entities": variacao["entities"]
                }
            })
    
    # Embaralha
    random.shuffle(dataset)
    
    # Divide em train/val/holdout (80/10/10)
    total = len(dataset)
    train_end = int(total * 0.8)
    val_end = int(total * 0.9)
    
    train = dataset[:train_end]
    val = dataset[train_end:val_end]
    holdout = dataset[val_end:]
    
    # Salva
    Path("datasets").mkdir(exist_ok=True)
    
    with open("datasets/gliner_train.jsonl", "w") as f:
        for item in train:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    
    with open("datasets/gliner_val.jsonl", "w") as f:
        for item in val:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    
    with open("datasets/gliner_holdout.jsonl", "w") as f:
        for item in holdout:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    
    print(f"Train: {len(train)} exemplos")
    print(f"Val: {len(val)} exemplos")
    print(f"Holdout: {len(holdout)} exemplos")
    print(f"Total: {len(dataset)} exemplos")

if __name__ == "__main__":
    main()