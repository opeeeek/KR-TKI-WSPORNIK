"""Sprawdzenia krzyżulców ściskanych (EN 1992-1-1 §6.5.2, §6.5.3(3), zał. J.3(1))."""
from __future__ import annotations

import math

from .checks_common import make, n, kN, mm, MPa, SIDE_NAME
from .core.results import Basis, Check, CheckStatus
from .core.units import Kind, Q
from .core.model import StmSettings
from .material_engine import Materials
from .normative_parameters import ParameterSet, SUPPORTED_EDITION
from .stm_generator import SideModel, StrutGeom


def strut_stress(C: float, w: float, t: float) -> float:
    """σ = C / (w·t) z kontrolą wymiarów."""
    s = (Q(C, Kind.FORCE) / (Q(w, Kind.LENGTH) * Q(t, Kind.LENGTH))).expect(Kind.STRESS)
    return s.v


def strut_checks(sm: SideModel, strut: StrutGeom, mats: Materials, ps: ParameterSet, st: StmSettings,
                 combo: str) -> list[Check]:
    ps.require(SUPPORTED_EDITION)
    p, s = sm.params, sm.state
    sd = p.side
    c = mats.concrete
    lim = p.sigma_strut
    if st.strut_limit == "6.55":
        clause = "EN 1992-1-1 §6.5.2(1), wzór (6.55)"
        lim_txt = f"σ_Rd,max = f_cd = {MPa(c.fcd)}"
        note = ("Przyjęto (6.55): brak rozciągania poprzecznego lub ściskanie poprzeczne — decyzja projektanta; "
                "dla krzyżulca butelkowego wspornika zwykle właściwy jest wzór (6.56).")
    else:
        clause = "EN 1992-1-1 §6.5.2(2), wzory (6.56), (6.57N)"
        lim_txt = (f"σ_Rd,max = 0,6·ν'·f_cd = 0,6·{n(c.nu_prime, 3)}·{n(c.fcd)} = {MPa(lim)}; "
                   f"ν' = 1 − {n(c.fck, 0)}/250 = {n(c.nu_prime, 3)}")
        note = "Krzyżulec w strefie z rozciąganiem poprzecznym (zarysowanej) — wzór (6.56)."
    symbols = {
        "C_Ed": "siła ściskająca w krzyżulcu",
        "w": "szerokość efektywna krzyżulca na granicy węzła",
        "t": "grubość efektywna krzyżulca (wymiar prostopadły do płaszczyzny modelu)",
        "σ_Rd,max": "nośność obliczeniowa krzyżulca",
        "ν'": "współczynnik redukcyjny (6.57N)",
    }
    out = []
    sA = strut_stress(s.C, s.w_A, p.t_A)
    sB = strut_stress(s.C, s.w_B, p.t_B)
    out.append(make(
        f"STRUT_{sd}_A", "Krzyżulce", f"Krzyżulec S{sd} ({SIDE_NAME[sd]}) — przekrój przy węźle A",
        clause, Basis.NORMATIVE,
        "σ_Ed = C_Ed / (w_A·t_A) ≤ σ_Rd,max;  w_A = a_ef·sin θ + u·cos θ (rys. 6.27)",
        {**symbols, "a_ef": "efektywna długość płyty oporowej", "u": "wysokość strefy cięgna (u = 2·c_t)"},
        f"w_A = {n(p.a_ef, 1)}·sin {n(s.theta_deg, 2)}° + {n(p.u, 1)}·cos {n(s.theta_deg, 2)}° = {mm(s.w_A, 1)}; "
        f"σ_Ed = {kN(s.C)}·10³ / ({n(s.w_A, 1)}·{n(p.t_A, 0)}) = {MPa(sA)};  {lim_txt}",
        sA, lim, Kind.STRESS, combo, f"member:S{sd}", [note], E_label="σ_Ed", R_label="σ_Rd,max"))
    out.append(make(
        f"STRUT_{sd}_B", "Krzyżulce", f"Krzyżulec S{sd} ({SIDE_NAME[sd]}) — przekrój przy węźle B",
        clause, Basis.NORMATIVE,
        "σ_Ed = C_Ed / (w_B·t_B) ≤ σ_Rd,max;  w_B = √(x_c² + a_B²) (węzeł hydrostatyczny)",
        {**symbols, "x_c": "wysokość strefy ściskanej przy licu", "a_B": "szerokość poziomej ścianki węzła B"},
        f"w_B = √({n(s.x_c, 1)}² + {n(s.a_B, 1)}²) = {mm(s.w_B, 1)}; σ_Ed = {kN(s.C)}·10³ / "
        f"({n(s.w_B, 1)}·{n(p.t_B, 0)}) = {MPa(sB)};  {lim_txt}",
        sB, lim, Kind.STRESS, combo, f"member:S{sd}", [note], E_label="σ_Ed", R_label="σ_Rd,max"))
    # Zakres nachylenia krzyżulca J.3(1)
    tan_t = s.tan_theta
    out.append(make(
        f"STRUT_{sd}_TANMIN", "Model", f"Nachylenie krzyżulca S{sd}: tan θ ≥ 1,0",
        "EN 1992-1-1 zał. J.3(1)", Basis.INFORMATIVE, "tan θ ≥ 1,0  (warunek: η = 1,0 / tan θ ≤ 1)",
        {"θ": "kąt nachylenia krzyżulca do osi cięgna"},
        f"tan θ = z0 / (ξ_A − ξ_B) = {n(s.z0, 1)} / {n(s.xi_A - s.xi_B, 1)} = {n(tan_t, 3)}",
        p.tan_min, tan_t, Kind.RATIO, combo, f"member:S{sd}", E_label="tan θ_min", R_label="tan θ"))
    out.append(make(
        f"STRUT_{sd}_TANMAX", "Model", f"Nachylenie krzyżulca S{sd}: tan θ ≤ 2,5",
        "EN 1992-1-1 zał. J.3(1)", Basis.INFORMATIVE, "tan θ ≤ 2,5",
        {"θ": "kąt nachylenia krzyżulca do osi cięgna"},
        f"tan θ = {n(tan_t, 3)} (θ = {n(s.theta_deg, 2)}°)",
        tan_t, p.tan_max, Kind.RATIO, combo, f"member:S{sd}", E_label="tan θ", R_label="tan θ_max"))
    # Kształt krzyżulca i ryzyko rozłupania — informacja
    return out


def splitting_force(C: float, a: float, b: float, H: float) -> tuple[float, str, str]:
    """Siła rozciągająca poprzecznie wg 6.5.3(3), wzory (6.58), (6.59).

    a — szerokość krzyżulca w węźle, b — dostępna szerokość rozchodzenia,
    H — długość obszaru (długość krzyżulca między węzłami)."""
    if b <= a:
        return 0.0, "brak rozchodzenia (b ≤ a)", "T = 0"
    if b <= H / 2.0:
        T = 0.25 * (b - a) / b * C
        return T, "nieciągłość częściowa (b ≤ H/2), wzór (6.58)", "T = ¼·(b − a)/b·F"
    h = H / 2.0
    T = max(0.25 * (1.0 - 0.7 * a / h) * C, 0.0)
    return T, "nieciągłość pełna (b > H/2), wzór (6.59), h = H/2", "T = ¼·(1 − 0,7·a/h)·F"


def splitting_check(sm: SideModel, strut: StrutGeom, R_links: float, links_desc: str, combo: str
                    ) -> tuple[Check, float]:
    s = sm.state
    sd = sm.params.side
    if strut.shape != "butelkowy":
        c = make(f"SPLIT_{sd}", "Rozłupywanie", f"Rozciąganie poprzeczne krzyżulca S{sd} (rozłupywanie)",
                 "EN 1992-1-1 §6.5.3(3), rys. 6.25", Basis.NORMATIVE, "T = f(a, b, H, F)",
                 {}, f"Krzyżulec pryzmatyczny (b_dost = {mm(strut.b_avail)} ≈ w) — brak rozchodzenia pola naprężeń.",
                 None, None, Kind.FORCE, combo, f"member:S{sd}", status=CheckStatus.NA)
        return c, 0.0
    best = (0.0, "", "", 0.0)
    for a in (s.w_A, s.w_B):
        T, regime, fml = splitting_force(s.C, a, strut.b_avail, strut.length)
        if T >= best[0]:
            best = (T, regime, fml, a)
    T, regime, fml, a = best
    c = make(
        f"SPLIT_{sd}", "Rozłupywanie", f"Zbrojenie przeciw rozłupywaniu krzyżulca S{sd} (krzyżulec butelkowy)",
        "EN 1992-1-1 §6.5.3(3), wzory (6.58)/(6.59), rys. 6.25", Basis.NORMATIVE,
        f"{fml};  T ≤ Σ A_sw·f_ywd·sin γ",
        {"F": "siła w krzyżulcu C_Ed", "a": "szerokość krzyżulca w węźle (węższy koniec)",
         "b": "dostępna szerokość rozchodzenia (z geometrii obrysu)", "H": "długość krzyżulca między węzłami",
         "γ": "kąt między prętem poprzecznym a osią krzyżulca"},
        f"{regime}: F = {kN(s.C)}, a = {mm(a, 1)}, b = {mm(strut.b_avail, 1)}, H = {mm(strut.length, 1)} → "
        f"T = {kN(T)};  nośność zbrojenia przecinającego krzyżulec: {links_desc} = {kN(R_links)}",
        T, R_links, Kind.FORCE, combo, f"member:S{sd}",
        ["Zastosowanie 6.5.3(3) do krzyżulca wspornika: H przyjęto jako długość krzyżulca między węzłami, "
         "b — dostępną szerokość w połowie długości (interpretacja inżynierska)."],
        E_label="T_Ed", R_label="T_Rd")
    return c, T
