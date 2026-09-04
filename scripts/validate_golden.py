import json
import jsonschema
from pathlib import Path

def main():
    schema_path = Path("contracts/semantic_interpreter_v1_1_2.schema.json")
    dataset_path = Path("tests/golden_dataset.jsonl")

    with open(schema_path) as f:
        schema = json.load(f)

    tests = []
    ids = set()
    invalid_json = 0
    schema_errors = 0
    duplicate_ids = 0

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

            try:
                jsonschema.validate(instance=data["expected"], schema=schema)
            except jsonschema.ValidationError as e:
                print(f"Erro de schema no teste {test_id}: {e.message}")
                schema_errors += 1

    total = len(ids)
    print(f"Golden Dataset")
    print(f"Tests: {total}")
    print(f"Schema valid: {total - schema_errors}")
    print(f"Invalid: {invalid_json + schema_errors + duplicate_ids}")
    print(f"Duplicate IDs: {duplicate_ids}")
    if invalid_json == 0 and schema_errors == 0 and duplicate_ids == 0:
        print("RESULT: PASS")
    else:
        print("RESULT: FAIL")

if __name__ == "__main__":
    main()