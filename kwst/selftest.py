"""Autotest aplikacji (także w wersji zbudowanej .exe): ``KrotkiWspornikST --selftest``.

Wykonuje analizę projektu domyślnego i wszystkich wariantów biblioteki, generuje raport PDF oraz
eksporty do katalogu tymczasowego i sprawdza powtarzalność wyników. Kod wyjścia 0 = OK."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path


def run_selftest(out=None) -> int:
    """W aplikacji okienkowej (brak konsoli) raport autotestu zapisywany jest do pliku selftest.log
    w katalogu danych aplikacji."""
    if out is None:
        if sys.stdout is not None:
            out = sys.stdout
        else:
            from .project_io import app_data_dir
            with open(app_data_dir() / "selftest.log", "w", encoding="utf-8") as f:
                return _run(f)
    return _run(out)


def _run(out) -> int:
    from .analysis import run_analysis
    from .core.model import Project
    from .project_io import load_library
    from .report_engine.exporters import export_csv_checks, export_dxf, export_excel, export_json
    from .report_engine.pdf_report import generate_pdf
    from .version import APP_NAME, __version__

    print(f"{APP_NAME} {__version__} — autotest", file=out)
    ok = True
    p = Project()
    r1 = run_analysis(p.current)
    r2 = run_analysis(p.current)
    print(f"  analiza domyślna: {r1.verdict.title}; powtarzalność: {'OK' if r1.fingerprint == r2.fingerprint else 'BŁĄD'}",
          file=out)
    ok &= r1.fingerprint == r2.fingerprint and not r1.errors
    bad = [i.name for i in r1.validation if not i.ok]
    print(f"  walidacja automatyczna: {'OK' if not bad else bad}", file=out)
    ok &= not bad
    for it in load_library():
        r = run_analysis(it.variant)
        fails = [c.id for c in r.checks if c.status.value == "NIE SPEŁNIONO"]
        good = not r.errors and not fails
        ok &= good
        print(f"  biblioteka {it.key}: {r.verdict.code} {'OK' if good else fails}", file=out)
    with tempfile.TemporaryDirectory() as d:
        dd = Path(d)
        for name, fn in (("raport.pdf", lambda f: generate_pdf(p, p.current, r1, f)),
                         ("dane.xlsx", lambda f: export_excel(p, p.current, r1, f)),
                         ("spr.csv", lambda f: export_csv_checks(r1, f)),
                         ("wyniki.json", lambda f: export_json(p, p.current, r1, f)),
                         ("rys.dxf", lambda f: export_dxf(p.current, r1, f))):
            try:
                fn(str(dd / name))
                size = (dd / name).stat().st_size
                print(f"  {name}: {size} B", file=out)
                ok &= size > 500
            except Exception as exc:  # noqa: BLE001
                print(f"  {name}: BŁĄD {exc}", file=out)
                ok = False
    print("WYNIK AUTOTESTU: " + ("OK" if ok else "BŁĄD"), file=out)
    return 0 if ok else 1
