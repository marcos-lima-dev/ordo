import sys
import json
from pathlib import Path
from .runner import BenchmarkRunner
from .adapters import ADAPTER_REGISTRY

def main():
    if len(sys.argv) < 2:
        print("Uso: python -m benchmark --candidate <nome>")
        print()
        print("Candidatos disponíveis:")
        for name in sorted(ADAPTER_REGISTRY.keys()):
            # Adiciona uma breve descrição para os principais
            if name == "perfect":
                desc = "(100% acerto, para validação do benchmark)"
            elif name == "broken":
                desc = "(introduz erros propositais)"
            elif name == "deterministic":
                desc = "(baseline determinística)"
            elif name == "tucano":
                desc = "(LLM generalista com prompt)"
            elif name == "nuextract":
                desc = "(especialista em extração)"
            elif name == "arandu":
                desc = "(modelo público para pt-BR, 1.7B)"
            elif name == "drummond":
                desc = "(modelo público para pt-BR, 1.1B)"
            elif name == "gliner_ptbr":
                desc = "(especialista em NER para pt-BR)"
            elif name == "gliner":
                desc = "(GLiNER base para NER)"
            elif name == "modular":
                desc = "(GLiNER + classificador de intenção)"
            else:
                desc = ""
            print(f"  {name} {desc}")
        print()
        print("Para tucano, opcionalmente especifique o tamanho:")
        print("  python -m benchmark --candidate tucano 1.5B")
        print("  python -m benchmark --candidate tucano 3.7B")
        print("  (padrão: 0.5B)")
        sys.exit(1)

    candidate_name = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--candidate" else None
    if not candidate_name:
        print("Erro: --candidate é obrigatório")
        sys.exit(1)

    if candidate_name not in ADAPTER_REGISTRY:
        print(f"Candidato inválido: {candidate_name}")
        print("Candidatos disponíveis:")
        for name in sorted(ADAPTER_REGISTRY.keys()):
            print(f"  {name}")
        sys.exit(1)

    # Instancia o adaptador
    adapter_class = ADAPTER_REGISTRY[candidate_name]

    # Se for Tucano, passa o tamanho
    if candidate_name == "tucano":
        model_size = sys.argv[3] if len(sys.argv) > 3 else "0.5B"
        adapter = adapter_class(model_size=model_size)
    else:
        adapter = adapter_class()

    runner = BenchmarkRunner(adapter)
    report = runner.run()

    # Salva relatório
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    timestamp = report["metadata"]["timestamp"].replace(":", "-").replace(".", "-")
    filename = f"benchmark_{adapter.name}_{timestamp}.json"
    filepath = reports_dir / filename
    with open(filepath, "w", encoding="utf-8") as f:
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