"""Sprawdzenia węzłów STM (EN 1992-1-1 §6.5.4) i docisku lokalnego (§6.7)."""
from __future__ import annotations

import math

from .checks_common import make, n, kN, mm, MPa, SIDE_NAME
from .core.results import Basis, Check, CheckStatus
from .core.units import Kind, Q
from .core.model import StmSettings
from .geometry_engine import GeometryModel
from .material_engine import Materials
from .normative_parameters import ParameterSet, SUPPORTED_EDITION
from .stm_generator import SideModel

NODE_DESC = {
    "CCC": ("k₁", "k1_node", "(6.60)", "6.5.4(4)a) — węzeł ściskany bez zakotwionych cięgien"),
    "CCT": ("k₂", "k2_node", "(6.61)", "6.5.4(4)b) — węzeł z cięgnem zakotwionym w jednym kierunku"),
    "CTT": ("k₃", "k3_node", "(6.62)", "6.5.4(4)c) — węzeł z cięgnami w więcej niż jednym kierunku"),
}


def classify_node(n_ties: int) -> str:
    if n_ties <= 0:
        return "CCC"
    if n_ties == 1:
        return "CCT"
    return "CTT"


def face_stress(F: float, length: float, t: float) -> float:
    return (Q(F, Kind.FORCE) / (Q(length, Kind.LENGTH) * Q(t, Kind.LENGTH))).expect(Kind.STRESS).v


def _limit_text(ntype: str, mats: Materials, ps: ParameterSet, inc: bool) -> tuple[float, str]:
    sym, key, eq, _ = NODE_DESC[ntype]
    k = ps.v(key)
    c = mats.concrete
    f = ps.v("node_increase") if inc else 1.0
    val = f * k * c.nu_prime * c.fcd
    txt = (f"σ_Rd,max = {'1,10·' if inc else ''}{sym}·ν'·f_cd = {'1,10·' if inc else ''}{n(k, 2)}·{n(c.nu_prime, 3)}·"
           f"{n(c.fcd)} = {MPa(val)}")
    return val, txt


def node_checks(sm: SideModel, mats: Materials, ps: ParameterSet, st: StmSettings, combo: str) -> list[Check]:
    ps.require(SUPPORTED_EDITION)
    p, s = sm.params, sm.state
    sd = p.side
    inc = bool(st.node_10pct and st.node_10pct_justification.strip())
    notes_inc = ([f"Zastosowano zwiększenie o 10% wg 6.5.4(5) — uzasadnienie projektanta: "
                  f"{st.node_10pct_justification.strip()}"] if inc else [])
    out = []
    limA, txtA = _limit_text("CCT", mats, ps, inc)
    sb = face_stress(p.V, p.a_ef, p.t_A)
    out.append(make(
        f"NODE_A_{sd}_BEAR", "Węzły", f"Węzeł A{sd} (CCT) — ścianka docisku pod płytą",
        "EN 1992-1-1 §6.5.4(4)b), wzór (6.61), rys. 6.27", Basis.NORMATIVE,
        "σ_Rd,1 = F_Ed / (a_ef·t_A) ≤ k₂·ν'·f_cd",
        {"F_Ed": "pionowa siła obliczeniowa", "a_ef": "efektywna długość płyty (a_p − 2|e|)",
         "t_A": "efektywna szerokość płyty (b_p − 2|e_y|)"},
        f"a_ef = {n(p.a_p, 0)} − 2·{n(abs(p.e_rel), 1)} = {mm(p.a_ef, 1)}; σ = {kN(p.V)}·10³ / ({n(p.a_ef, 1)}·"
        f"{n(p.t_A, 0)}) = {MPa(sb)};  {txtA}",
        sb, limA, Kind.STRESS, combo, f"node:A{sd}", notes_inc, E_label="σ_Ed", R_label="σ_Rd,max"))
    sA = face_stress(s.C, s.w_A, p.t_A)
    out.append(make(
        f"NODE_A_{sd}_STRUT", "Węzły", f"Węzeł A{sd} (CCT) — ścianka krzyżulca",
        "EN 1992-1-1 §6.5.4(4)b), wzór (6.61), rys. 6.27", Basis.NORMATIVE,
        "σ_Rd,2 = C_Ed / (a₂·t_A) ≤ k₂·ν'·f_cd;  a₂ = a_ef·sin θ + u·cos θ",
        {"C_Ed": "siła w krzyżulcu", "a₂": "szerokość ścianki krzyżulca w węźle", "u": "wysokość strefy cięgna"},
        f"a₂ = {mm(s.w_A, 1)}; σ = {kN(s.C)}·10³ / ({n(s.w_A, 1)}·{n(p.t_A, 0)}) = {MPa(sA)};  {txtA}",
        sA, limA, Kind.STRESS, combo, f"node:A{sd}", notes_inc, E_label="σ_Ed", R_label="σ_Rd,max"))
    limB, txtB = _limit_text("CCC", mats, ps, inc)
    sB = face_stress(s.Fc, s.x_c, p.t_B)
    out.append(make(
        f"NODE_B_{sd}", "Węzły", f"Węzeł B{sd} (CCC) przy licu słupa — strefa ściskana",
        "EN 1992-1-1 §6.5.4(4)a), wzór (6.60), §6.5.4(8)", Basis.NORMATIVE,
        "σ_Ed = F_c / (x_c·t_B) = V_Ed / (a_B·t_B) = C_Ed / (w_B·t_B) ≤ k₁·ν'·f_cd  (węzeł hydrostatyczny)",
        {"F_c": "pozioma siła ściskająca przy licu", "x_c": "wysokość strefy ściskanej",
         "a_B": "szerokość poziomej ścianki węzła", "t_B": "grubość efektywna"},
        f"σ = {kN(s.Fc)}·10³ / ({n(s.x_c, 1)}·{n(p.t_B, 0)}) = {MPa(sB)};  {txtB};  x_c = {mm(s.x_c, 1)} "
        f"(dobór: {sm.search.get('method', '—')})",
        sB, limB, Kind.STRESS, combo, f"node:B{sd}", notes_inc, E_label="σ_Ed", R_label="σ_Rd,max"))
    return out


def node_c_check(T_total: float, combo: str, double: bool) -> Check:
    txt = ("Węzeł zakotwienia cięgna w słupie (strefa słupa) — siła w cięgnie przekazywana na słup. "
           "Nośność strefy węzłowej słupa zależy od sił w słupie i jego zbrojenia — poza zakresem lokalnego "
           "modelu wspornika.")
    if double:
        txt = ("Cięgno ciągłe przez słup (wsporniki dwustronne) — różnica sił cięgien przekazywana na słup "
               "przyczepnością; strefa słupa wymaga osobnej weryfikacji.")
    return make("NODE_C", "Węzły", "Węzeł C — zakotwienie / przejście cięgna w słupie",
                "EN 1992-1-1 §6.5.4, J.3(4)", Basis.MODEL, "—", {}, txt + f" Siła: {kN(T_total)}.",
                T_total, None, Kind.FORCE, combo, "node:C", status=CheckStatus.VERIFY)


def local_bearing_check(gm: GeometryModel, sm: SideModel, mats: Materials, ps: ParameterSet, combo: str
                        ) -> Check:
    """Docisk lokalny pod płytą wg 6.7(2), wzór (6.63)."""
    p = sm.params
    sd = p.side
    sg = gm.sides[sd]
    c = mats.concrete
    a1 = p.a_ef            # wymiar w kierunku wysięgu
    b1 = p.t_A             # wymiar w poprzek
    # środek pola efektywnego = punkt przyłożenia wypadkowej na płycie (a_ef = a_p − 2|e|)
    x_center = sg.plate.xi_center + p.e_rel
    h_av = sg.depth_at(x_center)
    dist_end = sg.l_c - x_center
    dist_face = x_center
    d2 = min(3.0 * a1, a1 + h_av, 2.0 * dist_end, 2.0 * dist_face)
    lat = gm.b / 2.0 - abs(p.e_y)
    b2 = min(3.0 * b1, b1 + h_av, 2.0 * lat)
    d2 = max(d2, a1)
    b2 = max(b2, b1)
    Ac0 = a1 * b1
    Ac1 = d2 * b2
    ratio = math.sqrt(Ac1 / Ac0)
    FRdu = min(Ac0 * c.fcd * ratio, ps.v("bearing_max") * c.fcd * Ac0)
    return make(
        f"BEARING_{sd}", "Docisk", f"Docisk lokalny pod płytą oporową ({SIDE_NAME[sd]})",
        "EN 1992-1-1 §6.7(2), wzór (6.63), rys. 6.29", Basis.NORMATIVE,
        "F_Rdu = A_c0·f_cd·√(A_c1/A_c0) ≤ 3,0·f_cd·A_c0",
        {"A_c0": "pole obciążone (a_ef × b_ef)", "A_c1": "maksymalne obliczeniowe pole rozdziału (podobne, "
         "współśrodkowe, ograniczone krawędziami i wysokością h)", "h": "wysokość wspornika w miejscu obciążenia"},
        f"A_c0 = {n(a1, 1)}·{n(b1, 1)} = {n(Ac0, 0)} mm²; A_c1 = {n(d2, 1)}·{n(b2, 1)} = {n(Ac1, 0)} mm² "
        f"(d₂ ≤ min(3d₁; d₁+h; 2·odl. od krawędzi), h = {mm(h_av)}); F_Rdu = {n(Ac0, 0)}·{n(c.fcd)}·"
        f"{n(ratio, 3)} = {kN(FRdu)}",
        p.V, FRdu, Kind.FORCE, combo, f"node:A{sd}",
        ["Rozkład obciążenia przyjęto jako równomierny na powierzchni płyty (6.7(1)). Pole A_c1 ograniczono "
         "konserwatywnie odległością od lica słupa."], E_label="F_Ed", R_label="F_Rdu")


def manual_member_checks(model, solution, man, mats: Materials, ps: ParameterSet, st: StmSettings,
                         combo: str) -> list[Check]:
    """Sprawdzenia elementów modelu ręcznego (krzyżulce, cięgna, węzły)."""
    from .material_engine import strut_limit
    out: list[Check] = []
    c = mats.concrete
    s_lim, s_fml, _ = strut_limit(c, ps, st.strut_limit)
    mem = {m.id: m for m in man.members}
    ties_at: dict[str, int] = {n_.id: 0 for n_ in man.nodes}
    node_max: dict[str, tuple[float, str]] = {n_.id: (0.0, "") for n_ in man.nodes}
    for m in man.members:
        N = solution.forces.get(m.id, 0.0)
        if m.kind == "strut":
            if N > 1e-6:
                out.append(make(f"MAN_SIGN_{m.id}", "Model", f"Zgodność typu pręta {m.id} (krzyżulec)",
                                "EN 1992-1-1 §5.6.4, §6.5.1", Basis.MODEL, "N ≤ 0 dla krzyżulca", {},
                                f"N = {kN(N)} (rozciąganie) — pręt zadeklarowany jako krzyżulec przenosi rozciąganie.",
                                N, 0.0, Kind.FORCE, combo, f"member:{m.id}", status=CheckStatus.FAIL))
                continue
            C = -N
            if m.width <= 0 or m.thickness <= 0:
                out.append(make(f"MAN_STRUT_{m.id}", "Krzyżulce", f"Krzyżulec {m.id}", "EN 1992-1-1 §6.5.2",
                                Basis.NORMATIVE, "—", {}, "Brak szerokości/grubości krzyżulca.", None, None,
                                Kind.STRESS, combo, f"member:{m.id}", status=CheckStatus.FAIL,
                                conclusion="Nie podano wymiarów krzyżulca."))
                continue
            sig = face_stress(C, m.width, m.thickness)
            out.append(make(f"MAN_STRUT_{m.id}", "Krzyżulce", f"Krzyżulec {m.id}",
                            "EN 1992-1-1 §6.5.2", Basis.NORMATIVE, f"σ = C/(w·t) ≤ {s_fml}",
                            {"w": "szerokość podana przez użytkownika", "t": "grubość"},
                            f"σ = {kN(C)}·10³/({n(m.width, 1)}·{n(m.thickness, 0)}) = {MPa(sig)}; "
                            f"σ_Rd,max = {MPa(s_lim)}",
                            sig, s_lim, Kind.STRESS, combo, f"member:{m.id}", E_label="σ_Ed", R_label="σ_Rd,max"))
            for nid in (m.n1, m.n2):
                if sig > node_max[nid][0]:
                    node_max[nid] = (sig, m.id)
        else:
            ties_at[m.n1] += 1
            ties_at[m.n2] += 1
            if N < -1e-6:
                out.append(make(f"MAN_SIGN_{m.id}", "Model", f"Zgodność typu pręta {m.id} (cięgno)",
                                "EN 1992-1-1 §5.6.4, §6.5.1", Basis.MODEL, "N ≥ 0 dla cięgna", {},
                                f"N = {kN(N)} (ściskanie) — pręt zadeklarowany jako cięgno jest ściskany.",
                                -N, 0.0, Kind.FORCE, combo, f"member:{m.id}", status=CheckStatus.FAIL))
                continue
            TRd = m.As * mats.steel.fyd
            out.append(make(f"MAN_TIE_{m.id}", "Cięgna", f"Cięgno {m.id}", "EN 1992-1-1 §6.5.3(1)",
                            Basis.NORMATIVE, "T_Ed ≤ T_Rd = A_s·f_yd", {"A_s": "pole zbrojenia cięgna"},
                            f"T_Rd = {n(m.As, 0)}·{n(mats.steel.fyd, 1)} = {kN(TRd)}",
                            N, TRd, Kind.FORCE, combo, f"member:{m.id}", E_label="T_Ed", R_label="T_Rd"))
    sup = {s_.node: s_ for s_ in man.supports}
    for nd in man.nodes:
        ntype = classify_node(ties_at[nd.id])
        lim, txt = _limit_text(ntype, mats, ps, bool(st.node_10pct and st.node_10pct_justification.strip()))
        sig, mid = node_max[nd.id]
        if nd.id in sup and nd.id in solution.reactions:
            rx, ry = solution.reactions[nd.id]
            R = math.hypot(rx, ry)
            sp = sup[nd.id]
            t = min((mem[m].thickness for m in mem if nd.id in (mem[m].n1, mem[m].n2) and mem[m].kind == "strut"),
                    default=0.0)
            if sp.bearing_width > 0 and t > 0:
                sr = face_stress(R, sp.bearing_width, t)
                if sr > sig:
                    sig, mid = sr, "reakcja"
        if sig <= 0:
            continue
        out.append(make(f"MAN_NODE_{nd.id}", "Węzły", f"Węzeł {nd.id} ({ntype})",
                        f"EN 1992-1-1 §{NODE_DESC[ntype][3]}", Basis.NORMATIVE,
                        "max σ na ściankach węzła ≤ σ_Rd,max", {},
                        f"σ_max = {MPa(sig)} (od: {mid}); {txt}", sig, lim, Kind.STRESS, combo, f"node:{nd.id}",
                        E_label="σ_Ed", R_label="σ_Rd,max"))
    return out
