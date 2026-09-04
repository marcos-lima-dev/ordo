import re
import json
from pathlib import Path

# Caminho do arquivo .md (ajuste se necessário)
md_path = Path("catalogo-semantico-normalizado-v0.2.md")
output_path = Path("data/catalog.json")

# Lê o conteúdo do markdown
with open(md_path, "r", encoding="utf-8") as f:
    content = f.read()

# Localiza a tabela: linhas que começam com "| CQ-"
pattern = r"^\| (CQ-\d{2}) \| (.*?) \| (.*?) \| (.*?) \| (.*?) \| (.*?) \| (.*?) \| (.*?) \| (.*?) \| (.*?) \|$"
matches = re.findall(pattern, content, re.MULTILINE)

products = []
for match in matches:
    # match é uma tupla com 10 colunas
    product_id = match[0].strip()
    normalized_name = match[1].strip()
    brand = match[2].strip()
    unidade = match[3].strip()
    apresentacao = match[4].strip()
    peso = match[5].strip()
    embalagem = match[6].strip()
    qty_master = match[7].strip()
    preco_vista = match[8].strip()
    preco_prazo = match[9].strip()

    product = {
        "product_id": product_id,
        "original_name": normalized_name,  # mantém igual ao normalizado
        "normalized_name": normalized_name,
        "brand": brand,
        "unidade_precificacao": unidade,
        "apresentacao_individual": apresentacao,
        "peso_referencia_individual": peso,
        "embalagem_master": embalagem,
        "quantidade_unidades_master": qty_master,
        "preco_vista": preco_vista,
        "preco_prazo": preco_prazo
    }
    products.append(product)

# Salva o JSON
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(products, f, ensure_ascii=False, indent=2)

print(f"✅ {len(products)} produtos extraídos e salvos em {output_path}")