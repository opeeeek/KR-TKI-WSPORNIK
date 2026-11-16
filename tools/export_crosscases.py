"""Eksport przypadków kontrolnych do testu krzyżowego silnika JavaScript (tests/js/crosscheck.js).

Dla każdego wariantu zapisuje dane wejściowe (to_dict) oraz wyniki silnika referencyjnego Python:
werdykt, statusy i wartości E_d/R_d wszystkich sprawdzeń, błędy krytyczne, zbrojenie przyjęte w doborze.
"""
from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kwst.analysis import run_analysis  # noqa: E402
from kwst.core.model import (Variant, LoadAction, Layout, Construction, ManualNode, ManualMember,  # noqa: E402
                             ManualSupport, ManualLoad)
from kwst.core.serialization import to_dict  # noqa: E402

ST = {"SPEŁNIONO": "ok", "NIE SPEŁNIONO": "fail", "WYMAGA OSOBNEJ WERYFIKACJI": "warn", "NIE DOTYCZY": "na"}


def direct(V=400e3, H=0.0, **geo) -> Variant:
    v = Variant()
    v.loads.actions = [LoadAction(name="Ed", nature="design", category="G", V=V, H=H)]
    for k, val in geo.items():
        setattr(v.geometry.right, k, val)
    v.normative.ndp_confirmed = True
    return v


def bars(v, phi=20.0, n=4, layers=1, load="bend_down", col="bend_down"):
    m = v.reinforcement.main
    m.auto = False
    m.phi, m.n_per_layer, m.layers, m.anchor_load, m.anchor_column = phi, n, layers, load, col


def cases() -> list[tuple[str, Variant]]:
    out = [("domyślny (charakterystyczne + SGU)", Variant())]
    out.append(("01 pionowe", direct(400e3)))
    out.append(("02 pionowe + poziome", direct(400e3, 80e3)))
    v = direct(300e3, a_c=40.0); v.geometry.right.plate.length = 60.0; v.stm.node_b_position = "face"; bars(v)
    out.append(("03 bardzo krótki", v))
    v = direct(200e3, l_c=900.0, a_c=750.0, h_e=550.0); bars(v, 25.0, 6)
    out.append(("04 długi wysięg", v))
    v = direct(750e3); v.materials.concrete = "C25/30"
    out.append(("05 krytyczny krzyżulec", v))
    v = direct(320e3); v.geometry.right.plate.length = 60.0; v.geometry.right.plate.width = 150.0; v.stm.strut_limit = "6.55"
    out.append(("06 krytyczny węzeł", v))
    v = direct(400e3); bars(v, 12.0, 2)
    out.append(("07 za mało zbrojenia", v))
    v = direct(300e3); bars(v, 25.0, 4, load="straight", col="straight")
    out.append(("08 zakotwienie", v))
    out.append(("09 zła geometria a_c", direct(300e3, a_c=500.0)))
    out.append(("09b zła geometria h_e", direct(300e3, h_e=700.0)))
    v = direct(400e3); v.stm.mode = "manual"; m = v.stm.manual
    m.nodes = [ManualNode("A", 450, -50), ManualNode("B", 200, -500), ManualNode("C", -150, -50)]
    m.members = [ManualMember("S", "A", "B", "strut", 150, 400), ManualMember("T", "A", "C", "tie", 0, 400, 1000)]
    m.supports = [ManualSupport("B", True, True, 150), ManualSupport("C", True, True, 0)]
    m.loads = [ManualLoad("A", 0, -400e3)]
    out.append(("10 ręczny stateczny", v))
    v2 = copy.deepcopy(v); v2.stm.manual.supports = [ManualSupport("B", True, False, 150), ManualSupport("C", True, False, 0)]
    out.append(("10b ręczny zmienny", v2))
    v = direct(300e3, a_c=300.0, l_c=450.0); v.stm.lever_arm = "user"; v.stm.node_b_position = "face"; bars(v, 20.0, 5)
    v.geometry.right.z0_user = 300.0
    out.append(("11 granica tanθ=1", v))
    v = copy.deepcopy(v); v.geometry.right.z0_user = 295.0
    out.append(("11b tanθ<1", v))
    v = direct(300e3); bars(v, 25.0, 10)
    out.append(("12 nie mieści się", v))
    v = direct(900e3); v.geometry.b = 160.0; v.geometry.right.plate.width = 150.0
    out.append(("12b brak układu", v))
    v = direct(300e3); v.geometry.layout = Layout.DOUBLE
    v.loads.actions.append(LoadAction(name="EdL", side="L", nature="design", category="G", V=300e3))
    out.append(("dwustronny symetryczny", v))
    v = direct(300e3); v.geometry.layout = Layout.DOUBLE
    v.loads.actions.append(LoadAction(name="EdL", side="L", nature="design", category="G", V=150e3, H=30e3))
    out.append(("dwustronny niesymetryczny", v))
    v = direct(300e3); v.geometry.construction = Construction.PRECAST
    out.append(("prefabrykat", v))
    v = copy.deepcopy(v); v.normative.confirmed_params = ["fRd_dry", "table_10_2"]
    out.append(("prefabrykat potwierdzony", v))
    v = direct(350e3, x_slope=150.0, h_e=300.0)
    out.append(("skos dolnej krawędzi", v))
    v = direct(400e3); v.stm.lever_arm = "node_limit"
    out.append(("x_c z warunku węzła", v))
    v = direct(400e3); v.reinforcement.main.anchor_load = "welded_bar"; v.reinforcement.main.welded_bar_phi = 20.0
    out.append(("pręt przyspawany", v))
    v = direct(380e3, a_c=330.0, l_c=480.0, h_c=600.0, h_e=400.0)
    out.append(("a_c > 0,5 h_c (J.3(3))", v))
    v = Variant(); v.loads.actions[0].e_y = 40.0; v.materials.exposure = "XC4"; v.materials.concrete = "C40/50"
    out.append(("mimośród e_y, XC4", v))
    v = direct(400e3); v.reinforcement.main.alpha3_mode = "computed"; v.reinforcement.main.bond = "good"
    out.append(("α3 obliczane, dobra przyczepność", v))
    return out


def dump(r) -> dict:
    def num(x):
        if x is None:
            return None
        if isinstance(x, float) and not math.isfinite(x):
            return "inf" if x > 0 else "-inf"
        return x
    return {
        "verdict": r.verdict.code if r.verdict else None,
        "errors": [m.text for m in r.errors],
        "checks": [{"id": c.id, "status": ST[c.status.value], "E_d": num(c.E_d), "R_d": num(c.R_d), "eta": num(c.eta)}
                   for c in r.checks],
        "main": r.main.desc() if r.main else None,
        "As": r.main.As if r.main else None,
        "links": {sd: [len(ll.h_depths), ll.h_phi, len(ll.v_positions), ll.v_phi] for sd, ll in r.links.items()},
        "governing": r.governing,
        "T": {sd: sm.state.T for sd, sm in r.governing_stm.sides.items()} if r.governing_stm else {},
        "x_c": {sd: sm.state.x_c for sd, sm in r.governing_stm.sides.items()} if r.governing_stm else {},
        "schedule_kg": sum(b.mass for b in r.schedule),
    }


def main() -> None:
    data = []
    for name, v in cases():
        r = run_analysis(v)
        data.append({"name": name, "variant": to_dict(v), "py": dump(r)})
    out = ROOT / "tests" / "js" / "cases.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(out, len(data), "przypadków")


if __name__ == "__main__":
    main()
