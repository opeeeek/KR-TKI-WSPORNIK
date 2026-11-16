"""Test krzyżowy silnika JavaScript (program .exe / strona web) z silnikiem referencyjnym Python.

Dla każdego przypadku kontrolnego silnik JS musi dać ten sam werdykt, te same statusy i wartości E_d/R_d wszystkich
sprawdzeń, to samo zbrojenie i te same siły modelu STM. Wymaga Node.js (pomijany, gdy niedostępny)."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
NODE = shutil.which("node") or (str(Path("/opt/node22/bin/node")) if Path("/opt/node22/bin/node").exists() else None)


@pytest.mark.skipif(NODE is None, reason="brak Node.js")
def test_js_engine_matches_python():
    subprocess.run([sys.executable, str(ROOT / "tools" / "export_normdata.py")], check=True, capture_output=True)
    subprocess.run([sys.executable, str(ROOT / "tools" / "export_crosscases.py")], check=True, capture_output=True)
    r = subprocess.run([NODE, str(ROOT / "tests" / "js" / "crosscheck.js")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-4000:] + r.stderr[-2000:]
    assert "przypadków zgodnych" in r.stdout
