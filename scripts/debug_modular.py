import sys
from pathlib import Path

# Adiciona a raiz do projeto ao PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmark.adapters import ModularAdapter, DeterministicAdapter

adapter = ModularAdapter()
deterministic = DeterministicAdapter()

msg = "quero 10 quilos da manteiga sem sal"

print("=== DETERMINISTIC ===")
det_result = deterministic.predict(msg)
print(f"quantity.value: {det_result['quantity']['value']}")
print(f"quantity.unit: {det_result['quantity']['unit']}")

print("\n=== MODULAR ===")
mod_result = adapter.predict(msg)
print(f"quantity.value: {mod_result['quantity']['value']}")
print(f"quantity.unit: {mod_result['quantity']['unit']}")