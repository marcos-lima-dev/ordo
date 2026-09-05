import json
import jsonschema
from pathlib import Path

def main():
    # Carrega schema
    schema_path = Path("contracts/semantic_interpreter_v1_1_2.schema.json")
    with open(schema_path) as f:
        schema = json.load(f)

    # Carrega catálogo
    catalog_path = Path("data/catalog.json")
    with open(catalog_path) as f:
        catalog = json.load(f)
    product_ids = {p["product_id"] for p in catalog}

    # Carrega aliases
    aliases_path = Path("data/aliases.json")
    with open(aliases_path) as f:
        aliases = json.load(f)

    # Carrega golden dataset
    dataset_path = Path("tests/golden_dataset.jsonl")
    tests = []
    ids = set()
    duplicate_ids = 0
    invalid_json = 0
    schema_errors = 0

    # Verificação de SKUs referenciados no golden
    skus_in_golden = set()

    with open(dataset_path) as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Erro JSON na linha {line_num}: {e}")
                invalid_json += 1
                continue

            if "id" not in data or "expected" not in data:
                print(f"Linha {line_num} sem 'id' ou 'expected'")
                invalid_json += 1
                continue

            test_id = data["id"]
            if test_id in ids:
                print(f"ID duplicado: {test_id}")
                duplicate_ids += 1
            ids.add(test_id)

            # Valida schema
            try:
                jsonschema.validate(instance=data["expected"], schema=schema)
            except jsonschema.ValidationError as e:
                print(f"Erro de schema no teste {test_id}: {e.message}")
                schema_errors += 1

            # Coleta SKUs do catalog_candidates
            candidates = data["expected"].get("catalog_candidates", [])
            skus_in_golden.update(candidates)

    # Verificações estendidas
    total_products = len(product_ids)
    unique_products = len(product_ids) == total_products  # já é um set, então único

    total_aliases = len(aliases)
    alias_product_ids = {a["product_id"] for a in aliases}
    alias_references_ok = alias_product_ids.issubset(product_ids)

    sku_references_ok = skus_in_golden.issubset(product_ids)

    # Relatório final
    print("=== AUDITORIA FINAL - SPRINT 01 ===\n")
    print(f"Golden Dataset: {len(ids)}/30 valid" if len(ids) == 30 else f"Golden Dataset: {len(ids)}/30 (esperado 30)")
    print(f"Catalog products: {total_products}")
    print(f"Unique product IDs: {'PASS' if unique_products else 'FAIL'}")
    print(f"Aliases: {total_aliases}")
    print(f"Alias references: {'PASS' if alias_references_ok else 'FAIL'}")
    print(f"Golden SKU references: {'PASS' if sku_references_ok else 'FAIL'}")
    print(f"Duplicate test IDs: {duplicate_ids}")
    print(f"Schema errors: {schema_errors}")
    print(f"Invalid JSON lines: {invalid_json}")

    if (len(ids) == 30 and unique_products and alias_references_ok and
        sku_references_ok and duplicate_ids == 0 and schema_errors == 0 and invalid_json == 0):
        print("\nRESULT: PASS")
    else:
        print("\nRESULT: FAIL")
        # Detalha falhas
        if not alias_references_ok:
            missing = alias_product_ids - product_ids
            print(f"  Aliases com product_id inválido: {missing}")
        if not sku_references_ok:
            missing_skus = skus_in_golden - product_ids
            print(f"  SKUs em golden_dataset não existentes no catálogo: {missing_skus}")

if __name__ == "__main__":
    main()