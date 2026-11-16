"""Silnik referencyjny (Python) – wiersz poleceń.

    python -m kwst --selftest          test samokontroli silnika
    python -m kwst projekt.kwst        analiza projektu zapisanego w programie (podsumowanie wyników)

Program dla użytkownika to KrotkiWspornikST.exe / strona web (katalog web/, budowa: build_html.py) –
jego silnik JavaScript jest porównywany z tym silnikiem w testach krzyżowych (tests/js/crosscheck.js)."""
import sys


def main() -> int:
    args = sys.argv[1:]
    if not args or "--selftest" in args:
        from kwst.selftest import run_selftest
        return run_selftest()
    from kwst.analysis import run_analysis
    from kwst.project_io import load_project
    p = load_project(args[0])
    for v in p.variants:
        r = run_analysis(v)
        crit = r.critical()
        print(f"[{v.name}] {r.verdict.title} — {r.verdict.text}")
        if crit is not None:
            print(f"   element krytyczny: {crit.title} (η = {crit.eta:.3f})")
        for c in r.checks:
            if c.status.name in ("FAIL", "VERIFY"):
                print(f"   {c.status.value}: {c.title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
