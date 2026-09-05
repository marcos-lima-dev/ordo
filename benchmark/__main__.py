import sys
import json
from pathlib import Path
from .runner import BenchmarkRunner
from .adapters import PerfectMockAdapter, BrokenMockAdapter

def main():
    if len(sys.argv) < 2:
        print("Uso: python -m benchmark --candidate [perfect|broken]")
        sys.exit(1)

    candidate_name = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--candidate" else None
    if candidate_name == "perfect":
        adapter = PerfectMockAdapter()
    elif candidate_name == "broken":
        adapter = BrokenMockAdapter()
    else:
        print("Candidato inválido. Use 'perfect' ou 'broken'.")
        sys.exit(1)

    runner = BenchmarkRunner(adapter)
    report = runner.run()

    # Salva relatório
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    timestamp = report["metadata"]["timestamp"].replace(":", "-").replace(".", "-")
    filename = f"benchmark_{adapter.name}_{timestamp}.json"
    filepath = reports_dir / filename
    with open(filepath, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Exibe resumo
    print(f"Relatório salvo em {filepath}")
    print("\n=== RESULTADO ===")
    for key, val in report["summary"].items():
        print(f"{key}: {val}")
    print("\nField Accuracy:")
    for field, acc in report["field_accuracy"].items():
        print(f"  {field}: {acc:.2%}")
    if report["summary"]["unsafe_resolution_count"] > 0:
        print("\nATENÇÃO: Resoluções inseguras detectadas!")
        for u in report["unsafe_resolutions"]:
            print(f"  {u['test_id']}: esperado {u['expected_status']}, predito {u['predicted_status']}")

if __name__ == "__main__":
    main()