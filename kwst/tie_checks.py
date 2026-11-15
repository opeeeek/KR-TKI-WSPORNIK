"""Sprawdzenia cięgien rozciąganych (EN 1992-1-1 §6.5.3, §6.5.4(7), zał. J.3(4))."""
from __future__ import annotations

from .checks_common import make, n, kN, mm, mm2, SIDE_NAME
from .core.results import Basis, Check
from .core.units import Kind, Q
from .material_engine import Materials
from .normative_parameters import ParameterSet, SUPPORTED_EDITION
from .stm_generator import SideModel


def required_area(T: float, fyd: float) -> float:
    return (Q(max(T, 0.0), Kind.FORCE) / Q(fyd, Kind.STRESS)).expect(Kind.AREA).v


def tie_checks(sm: SideModel, As_prov: float, bars_desc: str, c_t_bars: float, mats: Materials,
               ps: ParameterSet, combo: str) -> list[Check]:
    ps.require(SUPPORTED_EDITION)
    p, s = sm.params, sm.state
    sd = p.side
    fyd = mats.steel.fyd
    As_req = required_area(s.T, fyd)
    TRd = (Q(As_prov, Kind.AREA) * Q(fyd, Kind.STRESS)).expect(Kind.FORCE).v
    out = [make(
        f"TIE_{sd}", "Cięgna", f"Cięgno główne T{sd} ({SIDE_NAME[sd]}) — nośność",
        "EN 1992-1-1 §6.5.3(1); zał. J.3, rys. J.5", Basis.NORMATIVE,
        "T_Ed = F_c + H_Ed ≤ T_Rd = A_s,prov·f_yd;  A_s,req = T_Ed / f_yd",
        {"T_Ed": "siła w cięgnie z równowagi modelu", "F_c": "pozioma siła w węźle B",
         "H_Ed": "siła pozioma (od słupa +)", "f_yd": "obliczeniowa granica plastyczności stali"},
        f"T_Ed = {kN(s.Fc)} + {kN(p.H)} = {kN(s.T)}; A_s,req = {kN(s.T)}·10³ / {n(fyd, 1)} = {mm2(As_req)}; "
        f"A_s,prov = {mm2(As_prov)} ({bars_desc}); T_Rd = {kN(TRd)}",
        s.T, TRd, Kind.FORCE, combo, f"member:T{sd}",
        [f"Równoważnie z rys. J.5: F_td = F_Ed·a_c/z0 + H_Ed·(a_H + z0)/z0 — a_c liczone do węzła B "
         f"(ξ_B = {n(s.xi_B, 1)} mm)."], E_label="T_Ed", R_label="T_Rd")]
    tol = ps.v("tie_axis_tol") * p.d
    dev = abs(p.c_t - c_t_bars)
    out.append(make(
        f"TIE_AXIS_{sd}", "Cięgna", f"Położenie osi cięgna T{sd} względem środka ciężkości zbrojenia",
        "EN 1992-1-1 §6.5.3, §6.5.4(7) — spójność modelu", Basis.MODEL,
        "|c_t,model − c_t,zbr| ≤ tol·d",
        {"c_t,model": "odległość osi cięgna w modelu od górnej krawędzi",
         "c_t,zbr": "odległość środka ciężkości prętów od górnej krawędzi"},
        f"|{n(p.c_t, 1)} − {n(c_t_bars, 1)}| = {mm(dev, 1)} ≤ {n(ps.v('tie_axis_tol'), 2)}·{n(p.d, 0)} = {mm(tol, 1)}",
        dev, tol, Kind.LENGTH, combo, f"member:T{sd}", E_label="Δ", R_label="tol", recommendation=True,
        notes=["Ręczna korekta d zmienia położenie cięgna i geometrię węzła A — przy odchyłce większej od "
               "tolerancji model wymaga oceny projektanta."]))
    return out
