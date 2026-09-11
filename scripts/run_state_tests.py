import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import json
from datetime import datetime

def main():
    result = pytest.main(["-v", "tests/test_state_invariants.py", "--json-report"])
    # Salva relatório em formato JSON
    report_path = Path("reports/state_invariants_report.json")
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "status": "COMPLETED",
            "note": "State invariants tests executed. Check pytest output for details."
        }, f)
    print(f"\nRelatório salvo em {report_path}")

if __name__ == "__main__":
    main()