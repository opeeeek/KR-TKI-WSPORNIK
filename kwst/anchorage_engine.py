"""Zakotwienia prętów zbrojeniowych (EN 1992-1-1 §8.3, §8.4) i ich sprawdzenia.

Zaimplementowano:
* f_bd = 2,25·η₁·η₂·f_ctd (8.2), z ograniczeniem f_ctk,0,05 do C60/75 (8.4.2(2));
* l_b,rqd = (φ/4)·(σ_sd/f_bd) (8.3);
* l_bd = α₁α₂α₃α₄α₅·l_b,rqd ≥ l_b,min (8.4), tabl. 8.2, (8.5), (8.6);
* c_d wg rys. 8.3 (pręty proste / odgięte, haki / pętle);
* minimalna średnica trzpienia: tabl. 8.1N oraz warunek (8.1) — §8.3(3).

Długość dostępną mierzy się zgodnie z J.3(4) i 6.5.4(7): od wewnętrznej
krawędzi płyty oporowej (strona obciążenia) oraz od położenia prętów
pionowych przy bliższej krawędzi słupa (strona słupa), do zewnętrznej
krawędzi pręta/odgięcia (konwencja rys. 8.1).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .checks_common import make, n, kN, mm, MPa
from .core.results import Basis, Check, CheckStatus
from .core.units import Kind, Q, bar_area
from .material_engine import Materials
from .normative_parameters import ParameterSet, SUPPORTED_EDITION

ANCHOR_LABEL = {
    "straight": "pręt prosty",
    "bend_down": "odgięcie 90° (rys. 8.1b)",
    "hook": "hak (rys. 8.1c)",
    "loop": "pętla pozioma (rys. 8.1d)",
    "welded_bar": "przyspawany pręt poprzeczny (rys. 8.1e)",
    "mechanical": "zakotwienie mechaniczne (wg ETA)",
    "continuous": "pręt ciągły przez słup",
}


@dataclass
class AnchorageInput:
    id: str
    title: str
    phi: float
    As_prov: float              # łączne pole prętów cięgna
    force: float                # siła do zakotwienia [N]
    anchor: str
    l_avail: float
    a_clear: float              # odstęp w świetle między prętami
    c1: float                   # otulina boczna
    c: float                    # otulina górna/dolna
    bond: str = "poor"
    alpha3_mode: str = "conservative"
    K: float = 0.05
    sum_Ast: float = 0.0
    element_ref: str = ""
    phi_t: float | None = None     # średnica pręta poprzecznego przyspawanego
    s_cc: float = 0.0              # rozstaw osiowy prętów kotwionych (l_t ≤ s_cc)


@dataclass
class AnchorageResult:
    inp: AnchorageInput
    fbd: float
    eta1: float
    eta2: float
    sigma_sd: float
    lb_rqd: float
    cd: float
    alphas: dict[str, float]
    lb_min: float
    lbd: float
    notes: list[str] = field(default_factory=list)
    Fbtd: float = 0.0
    method: str = "8.4"


def bond_strength(mats: Materials, ps: ParameterSet, phi: float, bond: str) -> tuple[float, float, float]:
    eta1 = 1.0 if bond == "good" else ps.v("eta1_poor")
    eta2 = 1.0 if phi <= 32 else (132.0 - phi) / 100.0
    fbd = ps.v("bond_coef") * eta1 * eta2 * mats.concrete.fctd_bond
    return fbd, eta1, eta2


def welded_bar_capacity(a: AnchorageInput, mats: Materials, ps: ParameterSet) -> tuple[float, str]:
    """Nośność zakotwienia jednym przyspawanym prętem poprzecznym wg §8.6(2), wzór (8.8N).

    F_btd = l_td·φ_t·σ_td ≤ F_wd;  l_td = 1,16·φ_t·(f_yd/σ_td)^0,5 ≤ l_t;
    σ_td = (f_ctd + σ_cm)/y ≤ 3·f_cd;  y = 0,015 + 0,14·e^(−0,18x);  x = 2·(c/φ_t) + 1.
    σ_cm = 0 (konserwatywnie). Wzór stosowany dla φ_t = 14–32 mm."""
    phi_t = a.phi_t or a.phi
    if not (14.0 <= phi_t <= 32.0):
        return 0.0, f"φ_t = {phi_t:.0f} mm poza zakresem 14–32 mm wzoru (8.8N) — nie uwzględniono F_btd."
    c = mats.concrete
    fyd = mats.steel.fyd
    x = 2.0 * (a.c / phi_t) + 1.0
    y = 0.015 + 0.14 * math.exp(-0.18 * x)
    s_td = min((c.fctd + 0.0) / y, 3.0 * c.fcd)
    lt = a.s_cc if a.s_cc > 0 else phi_t * 10.0
    ltd = min(1.16 * phi_t * math.sqrt(fyd / s_td), lt)
    Fwd = ps.v("fwd_factor") * bar_area(a.phi) * fyd
    F = min(ltd * phi_t * s_td, Fwd)
    txt = (f"(8.8N): x = 2·{n(a.c, 1)}/{n(phi_t, 0)} + 1 = {n(x, 3)}; y = {n(y, 4)}; σ_td = {n(s_td, 2)} MPa; "
           f"l_td = {n(ltd, 1)} mm; F_btd = min({n(ltd * phi_t * s_td / 1e3, 2)}; F_wd = {n(Fwd / 1e3, 2)}) = "
           f"{n(F / 1e3, 2)} kN/pręt")
    return F, txt


def anchorage_length(a: AnchorageInput, mats: Materials, ps: ParameterSet) -> AnchorageResult:
    """Długość zakotwienia; dla pręta poprzecznego przyspawanego przyjmuje się korzystniejszą
    z dwóch ścieżek normowych: α₄ = 0,7 (tabl. 8.2) albo redukcja σ_sd o F_btd/A_s (8.6(2)) z α₄ = 1,0."""
    if a.anchor == "welded_bar":
        r1 = _anchorage_length(a, mats, ps, welded_mode="alpha4")
        r2 = _anchorage_length(a, mats, ps, welded_mode="8.6")
        return r2 if r2.lbd < r1.lbd else r1
    return _anchorage_length(a, mats, ps)


def _anchorage_length(a: AnchorageInput, mats: Materials, ps: ParameterSet, welded_mode: str = "") -> AnchorageResult:
    ps.require(SUPPORTED_EDITION)
    phi = a.phi
    fbd, eta1, eta2 = bond_strength(mats, ps, phi, a.bond)
    sigma = (Q(max(a.force, 0.0), Kind.FORCE) / Q(a.As_prov, Kind.AREA)).expect(Kind.STRESS).v if a.As_prov > 0 \
        else math.inf
    sigma = min(sigma, mats.steel.fyd) if math.isfinite(sigma) else sigma
    notes: list[str] = []
    Fbtd = 0.0
    if welded_mode == "8.6":
        Fbtd, wtxt = welded_bar_capacity(a, mats, ps)
        red = Fbtd / bar_area(phi)
        notes.append(wtxt + f"; σ_sd zredukowane o F_btd/A_s = {n(red, 1)} MPa (8.6(2)).")
        sigma = max(sigma - red, 0.0)
    lb_rqd = (phi / 4.0) * (sigma / fbd)
    straight = a.anchor in ("straight", "welded_bar", "mechanical", "continuous")
    if a.anchor == "loop":
        cd = a.c
        cd_txt = "c_d = c (pętle, rys. 8.3c)"
    elif straight:
        cd = min(a.a_clear / 2.0, a.c1, a.c)
        cd_txt = "c_d = min(a/2; c₁; c) (pręty proste, rys. 8.3a)"
    else:
        cd = min(a.a_clear / 2.0, a.c1)
        cd_txt = "c_d = min(a/2; c₁) (odgięcia/haki, rys. 8.3b)"
    if straight:
        a1 = 1.0
        a2 = min(1.0, max(0.7, 1.0 - 0.15 * (cd - phi) / phi))
    else:
        a1 = 0.7 if cd > 3.0 * phi else 1.0
        a2 = min(1.0, max(0.7, 1.0 - 0.15 * (cd - 3.0 * phi) / phi))
    if a.alpha3_mode == "computed":
        As1 = bar_area(phi)
        lam = (a.sum_Ast - 0.25 * As1) / As1
        a3 = min(1.0, max(0.7, 1.0 - a.K * lam))
        notes.append(f"α₃: λ = (ΣA_st − 0,25·A_s)/A_s = {n(lam, 3)}, K = {n(a.K, 2)}.")
    else:
        a3 = 1.0
        notes.append("α₃ = 1,0 — konserwatywnie pominięto skrępowanie zbrojeniem poprzecznym.")
    a4 = 0.7 if (a.anchor == "welded_bar" and welded_mode != "8.6") else 1.0
    a5 = 1.0
    notes.append("α₅ = 1,0 — pominięto korzystny docisk poprzeczny (założenie bezpieczne).")
    prod235 = a2 * a3 * a5
    lim = ps.v("alpha235_min")
    if prod235 < lim:
        corr = lim / prod235
        a2 *= corr
        notes.append("Iloczyn α₂α₃α₅ ograniczono do 0,7 (8.5).")
    lb_min = max(ps.v("lbmin_ratio") * lb_rqd, 10.0 * phi, 100.0)
    lbd = max(a1 * a2 * a3 * a4 * a5 * lb_rqd, lb_min)
    res = AnchorageResult(a, fbd, eta1, eta2, sigma, lb_rqd, cd,
                          {"α1": a1, "α2": a2, "α3": a3, "α4": a4, "α5": a5}, lb_min, lbd, notes, Fbtd,
                          "8.6" if welded_mode == "8.6" else "8.4")
    res.notes.insert(0, cd_txt + f" = {n(cd, 1)} mm")
    return res


def anchorage_check(a: AnchorageInput, mats: Materials, ps: ParameterSet, combo: str, clause_extra: str = ""
                    ) -> tuple[Check, AnchorageResult | None]:
    if a.anchor == "mechanical":
        c = make(a.id, "Zakotwienie", a.title, "EN 1992-1-1 §8.4.1(2), §8.8; ETA urządzenia", Basis.NORMATIVE,
                 "Nośność zakotwienia mechanicznego wg aprobaty (ETA) / badań", {},
                 f"Siła do zakotwienia: {kN(a.force)}. Nośność głowicy/urządzenia nie jest obliczana przez program.",
                 a.force, None, Kind.FORCE, combo, a.element_ref, status=CheckStatus.VERIFY)
        return c, None
    r = anchorage_length(a, mats, ps)
    al = r.alphas
    sub = (f"f_bd = 2,25·{n(r.eta1, 2)}·{n(r.eta2, 2)}·{n(mats.concrete.fctd_bond, 3)} = {MPa(r.fbd, 3)}; "
           f"σ_sd = {kN(a.force)}·10³/{n(a.As_prov, 0)}{' − F_btd/A_s' if r.method == '8.6' else ''} = {MPa(r.sigma_sd, 1)}; "
           f"l_b,rqd = ({n(a.phi, 0)}/4)·({n(r.sigma_sd, 1)}/{n(r.fbd, 3)}) = {mm(r.lb_rqd, 0)}; "
           f"α₁…α₅ = {n(al['α1'], 2)}·{n(al['α2'], 3)}·{n(al['α3'], 2)}·{n(al['α4'], 2)}·{n(al['α5'], 2)}; "
           f"l_b,min = {mm(r.lb_min, 0)}; l_bd = {mm(r.lbd, 0)}; l_dost = {mm(a.l_avail, 0)}")
    c = make(a.id, "Zakotwienie", a.title + f" — {ANCHOR_LABEL.get(a.anchor, a.anchor)}",
             "EN 1992-1-1 §8.4.2–8.4.4, wzory (8.2)–(8.6), tabl. 8.2" + clause_extra, Basis.NORMATIVE,
             "l_bd = α₁·α₂·α₃·α₄·α₅·(φ/4)·(σ_sd/f_bd) ≥ l_b,min;  l_bd ≤ l_dost",
             {"f_bd": "graniczne naprężenie przyczepności (8.2)", "η₁": "warunki przyczepności (rys. 8.2)",
              "σ_sd": "naprężenie w pręcie na początku zakotwienia", "c_d": "otulina/odstęp wg rys. 8.3",
              "l_dost": "długość dostępna mierzona wg J.3(4) / rys. 8.1"},
             sub, r.lbd, a.l_avail, Kind.LENGTH, combo, a.element_ref, r.notes,
             E_label="l_bd", R_label="l_dost")
    if a.anchor == "welded_bar":
        c.notes.append("Jakość połączenia spawanego wymaga wykazania (8.6(1), EN ISO 17660) — F_wd przyjęto wg "
                       "parametru 'fwd_factor'.")
        c.notes.append("Ścieżka obliczeń: " + ("redukcja σ_sd o F_btd (8.6(2)), α₄ = 1,0" if r.method == "8.6"
                                               else "α₄ = 0,7 (tabl. 8.2)"))
    return c, r


def mandrel_min_table(phi: float, ps: ParameterSet) -> float:
    return (ps.v("mandrel_small") if phi <= 16 else ps.v("mandrel_large")) * phi


def mandrel_checks(id_: str, title: str, phi: float, phi_m: float, Fbt: float, ab: float, mats: Materials,
                   ps: ParameterSet, combo: str, ref: str) -> list[Check]:
    """Tabl. 8.1N oraz warunek (8.1) dla odgięć/pętli."""
    out = []
    tmin = mandrel_min_table(phi, ps)
    out.append(make(f"{id_}_T81", "Zakotwienie", f"{title} — min. średnica trzpienia (tabl. 8.1N)",
                    "EN 1992-1-1 §8.3(2), tabl. 8.1N", Basis.NORMATIVE, "φ_m ≥ φ_m,min (4φ dla φ ≤ 16; 7φ dla φ > 16)",
                    {"φ_m": "średnica trzpienia (wewnętrzna średnica gięcia)"},
                    f"φ_m,min = {mm(tmin)}; φ_m = {mm(phi_m)}", tmin, phi_m, Kind.LENGTH, combo, ref,
                    E_label="φ_m,min", R_label="φ_m"))
    fck_cap = ps.v("fcd_mandrel_cap")
    c = mats.concrete
    fcd = min(c.fcd, c.alpha_cc * fck_cap / c.gamma_c)
    req = Fbt * (1.0 / ab + 1.0 / (2.0 * phi)) / fcd
    out.append(make(f"{id_}_81", "Zakotwienie", f"{title} — docisk betonu w odgięciu, wzór (8.1)",
                    "EN 1992-1-1 §8.3(3), wzór (8.1)", Basis.NORMATIVE,
                    "φ_m,min ≥ F_bt·((1/a_b) + 1/(2φ)) / f_cd",
                    {"F_bt": "siła rozciągająca w pręcie na początku odgięcia (przyjęto pełną)",
                     "a_b": "połowa rozstawu osiowego prętów (lub otulina + φ/2 przy krawędzi)",
                     "f_cd": "≤ wartość dla C55/67"},
                    f"F_bt = {kN(Fbt, 2)}, a_b = {mm(ab, 1)}: φ_m,min = {n(Fbt, 0)}·(1/{n(ab, 1)} + 1/{n(2 * phi, 0)})"
                    f"/{n(fcd, 2)} = {mm(req, 0)}; φ_m = {mm(phi_m)}",
                    req, phi_m, Kind.LENGTH, combo, ref, E_label="φ_m,req", R_label="φ_m"))
    return out
