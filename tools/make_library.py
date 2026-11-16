"""Generuje bibliotekę typowych wsporników (kwst/resources/library/*.json).

Każdy wariant jest sprawdzany pełną analizą — do biblioteki trafiają wyłącznie
przypadki bez błędów i bez niespełnionych sprawdzeń."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kwst.analysis import run_analysis  # noqa: E402
from kwst.core.model import Variant, LoadAction, Layout, Construction  # noqa: E402
from kwst.core.serialization import to_dict  # noqa: E402


def precast_beam() -> Variant:
    v = Variant(name="Prefabrykat — oparcie belki")
    g = v.geometry
    g.construction = Construction.PRECAST
    g.precast.restraint_considered = True
    g.right.l_c, g.right.h_c, g.right.h_e, g.right.a_c = 400.0, 550.0, 350.0, 250.0
    v.loads.actions = [
        LoadAction(name="G1", category="G", V=180e3, source="beam_reaction", note="Reakcja belki — ciężar własny i stałe"),
        LoadAction(name="Q1", category="Q_B", V=120e3, source="beam_reaction", note="Reakcja belki — użytkowe"),
        LoadAction(name="H1", category="G", V=0.0, H=40e3, source="other",
                   note="Siła od więzów (skurcz/pełzanie/temperatura) — wartość przyjęta przez projektanta"),
    ]
    return v


def monolithic_constant() -> Variant:
    v = Variant(name="Monolityczny — stała wysokość")
    r = v.geometry.right
    r.l_c, r.h_c, r.h_e, r.a_c = 420.0, 500.0, 500.0, 240.0
    v.loads.actions = [LoadAction(name="G1", category="G", V=140e3), LoadAction(name="Q1", category="Q_C", V=90e3)]
    return v


def tapered() -> Variant:
    v = Variant(name="Zmienna wysokość — skos od x_s")
    r = v.geometry.right
    r.l_c, r.h_c, r.h_e, r.x_slope, r.a_c = 450.0, 600.0, 380.0, 150.0, 260.0
    v.loads.actions = [LoadAction(name="G1", category="G", V=200e3), LoadAction(name="Q1", category="Q_B", V=120e3)]
    return v


def double_sym() -> Variant:
    v = Variant(name="Wsporniki dwustronne symetryczne")
    v.geometry.layout = Layout.DOUBLE
    v.geometry.left_mirror = True
    r = v.geometry.right
    r.l_c, r.h_c, r.h_e, r.a_c = 400.0, 550.0, 350.0, 250.0
    v.loads.actions = [
        LoadAction(name="G1P", side="R", category="G", V=160e3), LoadAction(name="Q1P", side="R", category="Q_B", V=90e3),
        LoadAction(name="G1L", side="L", category="G", V=160e3), LoadAction(name="Q1L", side="L", category="Q_B", V=90e3),
    ]
    return v


def eccentric() -> Variant:
    v = Variant(name="Obciążenie mimośrodowe")
    r = v.geometry.right
    r.l_c, r.h_c, r.h_e, r.a_c = 450.0, 600.0, 400.0, 250.0
    r.plate.length, r.plate.width = 180.0, 300.0
    v.loads.actions = [LoadAction(name="G1", category="G", V=150e3, e_x=15.0, e_y=20.0,
                                  note="Mimośród od podatności oparcia belki"),
                       LoadAction(name="Q1", category="Q_B", V=100e3, e_x=15.0, e_y=20.0)]
    return v


def design_values_h() -> Variant:
    v = Variant(name="Wartości obliczeniowe V_Ed + H_Ed")
    r = v.geometry.right
    r.l_c, r.h_c, r.h_e, r.a_c = 450.0, 600.0, 400.0, 260.0
    v.materials.concrete = "C35/45"
    v.loads.actions = [LoadAction(name="Ed", nature="design", category="G", V=380e3, H=70e3,
                                  note="Wartości obliczeniowe z analizy globalnej (bez ponownego mnożenia przez γ)")]
    return v


PRESETS = {
    "01_prefabrykat_belka": (precast_beam, "Wspornik słupa prefabrykowanego pod belkę z siłą poziomą od więzów."),
    "02_monolityczny_staly": (monolithic_constant, "Wspornik monolityczny o stałej wysokości, obciążenie pionowe."),
    "03_zmienna_wysokosc": (tapered, "Wspornik o zmiennej wysokości ze skosem dolnej krawędzi od x_s = 150 mm."),
    "04_dwustronny": (double_sym, "Wsporniki dwustronne symetryczne z cięgnem ciągłym przez słup."),
    "05_mimosrodowy": (eccentric, "Obciążenie z mimośrodem podłużnym i poprzecznym (skręcanie — osobna weryfikacja)."),
    "06_obliczeniowe_H": (design_values_h, "Wartości obliczeniowe V_Ed i H_Ed podane bezpośrednio."),
}


def main() -> int:
    out = ROOT / "kwst" / "resources" / "library"
    out.mkdir(parents=True, exist_ok=True)
    bad = 0
    for key, (fn, desc) in PRESETS.items():
        v = fn()
        r = run_analysis(v)
        fails = [c.id for c in r.checks if c.status.value == "NIE SPEŁNIONO"]
        ok = r.verdict.code in ("PASS_SCOPE", "CONDITIONAL") and not fails and not r.errors
        print(f"{key}: {r.verdict.code} {r.main.desc() if r.main else '-'} {'OK' if ok else 'FAIL ' + str(fails)}")
        if not ok:
            bad += 1
            continue
        (out / f"{key}.json").write_text(json.dumps({"title": v.name, "description": desc, "variant": to_dict(v)},
                                                    ensure_ascii=False, indent=1), encoding="utf-8")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
