from typing import Dict, Any
from order.state import OrderState

class StateEvaluator:
    @staticmethod
    def compare(expected: Dict[str, Any], actual: Dict[str, Any]) -> Dict[str, Any]:
        """Compara dois estados e retorna diferenças."""
        differences = []
        expected_items = expected.get("items", [])
        actual_items = actual.get("items", [])

        if len(expected_items) != len(actual_items):
            differences.append(f"Number of items mismatch: expected {len(expected_items)}, got {len(actual_items)}")
        else:
            for i, (exp, act) in enumerate(zip(expected_items, actual_items)):
                for key in exp:
                    if exp[key] != act.get(key):
                        differences.append(f"Item {i}: {key} mismatch: expected {exp[key]}, got {act.get(key)}")

        expected_status = expected.get("status")
        actual_status = actual.get("status")
        if expected_status != actual_status:
            differences.append(f"Status mismatch: expected {expected_status}, got {actual_status}")

        return {
            "match": len(differences) == 0,
            "differences": differences,
        }