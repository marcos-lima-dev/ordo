import json
import random
from pathlib import Path

# Lista de produtos do catálogo (exemplos)
PRODUTOS = [
    "manteiga sem sal",
    "manteiga com sal",
    "provolone",
    "gorgonzola",
    "brie",
    "camembert",
    "emmental",
    "gouda",
    "parmesão",
    "mussarela",
    "queijo prato",
    "queijo minas",
    "requeijão",
    "cream cheese",
    "catupiry",
    "ricota",
    "queijo coalho",
    "tomate seco",
    "iogurte",
    "creme de leite",
]

# Marcas (com variações)
MARCAS = [
    "Tânia",
    "Coyote",
    "São Vicente",
    "Catupiry",
    "Roseli",
    "Larisol",
    "Villani",
    "Serta Norte",
    "Gran Parma",
    "Dona Rosa",
]

# Apresentações
APRESENTACOES = [
    "forma",
    "formas",
    "bisnaga",
    "bisnagas",
    "peça",
    "peças",
    "pote",
    "potes",
    "saco",
    "sacos",
    "garrafa",
    "garrafas",
    "caixa",
    "caixas",
    "barra",
    "barras",
    "bloco",
    "blocos",
    "cartela",
    "cartelas",
    "balde",
    "baldes",
    "pacote",
    "pacotes",
    "fração",
    "vácuo",
    "unidade",
]

# Variações de introdução
INTRODUCOES = [
    "quero", "me manda", "coloca", "bota", "manda", 
    "gostaria de", "queria", "poderia me enviar", "preciso de"
]

# Modelo de anotação: (text, entities)
def gerar_exemplo_entidades():
    produto = random.choice(PRODUTOS)
    marca = random.choice(MARCAS) if random.random() < 0.4 else None
    apresentacao = random.choice(APRESENTACOES) if random.random() < 0.3 else None
    introducao = random.choice(INTRODUCOES)

    # Monta texto
    if marca and apresentacao:
        texto = f"{introducao} {random.randint(1,10)} {apresentacao} de {produto} da {marca}"
    elif marca:
        texto = f"{introducao} {random.randint(1,10)} kg de {produto} da {marca}"
    elif apresentacao:
        texto = f"{introducao} {random.randint(1,10)} {apresentacao} de {produto}"
    else:
        texto = f"{introducao} {random.randint(1,10)} kg de {produto}"

    # Entidades
    entities = []
    # Encontra posição do produto
    if produto in texto:
        start = texto.find(produto)
        end = start + len(produto)
        entities.append({"text": produto, "label": "PRODUCT", "start": start, "end": end})
    if marca and marca in texto:
        start = texto.find(marca)
        end = start + len(marca)
        entities.append({"text": marca, "label": "BRAND", "start": start, "end": end})
    if apresentacao and apresentacao in texto:
        start = texto.find(apresentacao)
        end = start + len(apresentacao)
        entities.append({"text": apresentacao, "label": "PRESENTATION", "start": start, "end": end})

    return {"text": texto, "entities": entities}

def main():
    # Gera dataset
    exemplos = [gerar_exemplo_entidades() for _ in range(300)]
    random.shuffle(exemplos)

    train = exemplos[:200]
    val = exemplos[200:250]
    holdout = exemplos[250:]

    Path("datasets/entities").mkdir(parents=True, exist_ok=True)

    with open("datasets/entities/train.jsonl", "w") as f:
        for e in train:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    with open("datasets/entities/val.jsonl", "w") as f:
        for e in val:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    with open("datasets/entities/holdout.jsonl", "w") as f:
        for e in holdout:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    print(f"Train: {len(train)}")
    print(f"Val: {len(val)}")
    print(f"Holdout: {len(holdout)}")

if __name__ == "__main__":
    main()