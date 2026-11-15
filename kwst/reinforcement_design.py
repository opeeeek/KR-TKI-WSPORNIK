"""Projektowanie i konstruowanie zbrojenia wspornika.

* otulina wg §4.4.1 (tabl. 4.2, 4.4N), odstępy prętów wg §8.2;
* układ zbrojenia głównego (warstwy, rozstaw, środek ciężkości c_t);
* układ strzemion poziomych / pionowych / prętów ukośnych;
* sprawdzenia konstrukcyjne: zał. J.3(2), J.3(3), V_Rd,c (6.2.2), A_s,min/A_s,max,
  fizyczna wykonalność (mieszczenie się prętów, odgięć, pętli);
* automatyczny dobór prętów i strzemion (tylko układy fizycznie wykonalne);
* zestawienie stali z automatycznym oznaczeniem pozycji.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable

from .checks_common import make, n, kN, mm, mm2, MPa
from .core.model import MaterialsInput, ReinforcementInput, MainBarsInput, LinksInput, GeometryInput, Layout
from .core.results import Basis, Check, CheckStatus
from .core.units import Kind, bar_area, bar_unit_mass
from .geometry_engine import GeometryModel
from .material_engine import Materials
from .normative_parameters import ParameterSet, EXPOSURE_GROUP, TABLE_4_4N, STRUCTURAL_CLASSES

LINK_DIAMETERS = [8.0, 10.0, 12.0, 14.0, 16.0]


@dataclass
class CoverResult:
    exposure: str
    structural_class: str
    c_min_dur: float
    delta_c_dev: float
    c_nom_req_link: float
    c_nom_req_main: float
    c_nom: float                # przyjęta otulina nominalna do zbrojenia zewnętrznego (strzemion)
    c_top_main: float           # otulina górna prętów głównych
    c_side_main: float          # otulina boczna prętów głównych
    phi_link_outer: float
    user: bool


def c_min_dur(m: MaterialsInput) -> float:
    grp = EXPOSURE_GROUP.get(m.exposure)
    if grp is None:
        raise ValueError(f"Nieobsługiwana klasa ekspozycji {m.exposure}")
    if m.structural_class not in STRUCTURAL_CLASSES:
        raise ValueError(f"Nieznana klasa konstrukcji {m.structural_class}")
    return float(TABLE_4_4N[grp][STRUCTURAL_CLASSES.index(m.structural_class)])


def cover_requirements(m: MaterialsInput, ps: ParameterSet, phi_main: float, phi_hlink: float,
                       phi_vlink: float, has_v: bool, has_h: bool) -> CoverResult:
    cdur = c_min_dur(m)
    add = ps.v("delta_c_dur_gamma") - ps.v("delta_c_dur_st") - ps.v("delta_c_dur_add")
    dev = m.delta_c_dev
    extra = 5.0 if m.d_g > 32 else 0.0
    phi_link = max(phi_hlink if has_h else 0.0, phi_vlink if has_v else 0.0)
    req_link = max(phi_link + extra, cdur + add, 10.0) + dev if phi_link > 0 else 0.0
    req_main = max(phi_main + extra, cdur + add, 10.0) + dev
    if m.c_nom_user is not None:
        c_nom = m.c_nom_user
        user = True
    else:
        # c_nom do zbrojenia zewnętrznego; pręty główne: od góry c_nom + φ_v (lub c_nom bez strzemion pionowych),
        # z boku c_nom + φ_strzemion
        need_top = req_main - (phi_vlink if has_v else 0.0)
        need_side = req_main - phi_link
        c_nom = math.ceil(max(req_link, need_top, need_side) / 5.0 - 1e-9) * 5.0
        user = False
    c_top = c_nom + (phi_vlink if has_v else 0.0)
    c_side = c_nom + phi_link
    return CoverResult(m.exposure, m.structural_class, cdur, dev, req_link, req_main, c_nom, c_top, c_side,
                       phi_link, user)


def s_min(phi: float, d_g: float, ps: ParameterSet) -> float:
    return max(ps.v("spacing_k1") * phi, d_g + ps.v("spacing_k2"), 20.0)


@dataclass
class MainLayout:
    phi: float
    n: int
    layers: int
    gap_v: float
    s_min: float
    a_clear: float
    c_t: float
    layer_depths: list[float]
    z_positions: list[float]
    As: float
    fits: bool
    issues: list[str] = field(default_factory=list)

    @property
    def total_bars(self) -> int:
        return self.n * self.layers

    def desc(self) -> str:
        lay = f" w {self.layers} warstwach" if self.layers > 1 else ""
        return f"{self.total_bars}φ{self.phi:.0f}{lay}"

    @property
    def s_cc(self) -> float:
        return self.a_clear + self.phi


def main_layout(b: float, cover: CoverResult, phi: float, n_: int, layers: int, gap: float | None, d_g: float,
                ps: ParameterSet) -> MainLayout:
    smin = s_min(phi, d_g, ps)
    gap_v = gap if gap is not None else smin
    issues = []
    if n_ < 2:
        issues.append("Wymagane co najmniej 2 pręty w warstwie (konstrukcyjnie — pręty w narożach strzemion).")
    width = b - 2.0 * cover.c_side_main
    a_clear = (width - n_ * phi) / (n_ - 1) if n_ >= 2 else math.inf
    fits = True
    if n_ >= 2 and a_clear < smin - 1e-9:
        fits = False
        issues.append(f"Odstęp w świetle a = {a_clear:.1f} mm < s_min = {smin:.1f} mm.")
    if layers > 1 and gap_v < smin - 1e-9:
        fits = False
        issues.append(f"Odstęp warstw {gap_v:.1f} mm < s_min = {smin:.1f} mm.")
    if n_ < 2:
        fits = False
    depths = [cover.c_top_main + phi / 2.0 + k * (phi + gap_v) for k in range(layers)]
    c_t = sum(depths) / layers
    z0 = -b / 2.0 + cover.c_side_main + phi / 2.0
    zs = [z0 + i * (a_clear + phi) for i in range(n_)] if n_ >= 2 else [0.0]
    return MainLayout(phi, n_, layers, gap_v, smin, a_clear, c_t, depths, zs, n_ * layers * bar_area(phi), fits,
                      issues)


@dataclass
class LinksLayout:
    h_phi: float
    h_depths: list[float]          # głębokości osi strzemion poziomych od górnej krawędzi
    v_phi: float
    v_positions: list[float]       # ξ strzemion pionowych od lica
    i_phi: float
    i_count: int
    h_zone: float
    issues: list[str] = field(default_factory=list)
    fits: bool = True

    @property
    def As_h(self) -> float:
        return 2.0 * len(self.h_depths) * bar_area(self.h_phi)

    @property
    def As_v(self) -> float:
        return 2.0 * len(self.v_positions) * bar_area(self.v_phi)

    @property
    def As_i(self) -> float:
        return 2.0 * self.i_count * bar_area(self.i_phi)

    def desc_h(self) -> str:
        return f"{len(self.h_depths)} strz. poz. 2-cięte φ{self.h_phi:.0f}" if self.h_depths else "brak strz. poziomych"

    def desc_v(self) -> str:
        return f"{len(self.v_positions)} strz. pion. 2-cięte φ{self.v_phi:.0f}" if self.v_positions else \
            "brak strz. pionowych"


def links_layout(gm: GeometryModel, side: str, ml: MainLayout, cover: CoverResult, li: LinksInput, d: float,
                 xi_A: float, d_g: float, ps: ParameterSet) -> LinksLayout:
    sg = gm.sides[side]
    issues: list[str] = []
    fits = True
    zone = li.h_zone if li.h_zone is not None else ps.v("h_link_zone") * d
    h_depths: list[float] = []
    if li.h_count > 0:
        smin_h = s_min(li.h_phi, d_g, ps)
        y_first = ml.layer_depths[-1] + (ml.phi + li.h_phi) / 2.0 + ml.s_min
        y_end = max(ml.c_t + zone, y_first)
        y_lim = sg.h_c - cover.c_nom - li.h_phi / 2.0
        if y_end > y_lim:
            y_end = y_lim
        if li.h_count == 1:
            h_depths = [y_first]
        else:
            h_depths = [y_first + (y_end - y_first) * k / (li.h_count - 1) for k in range(li.h_count)]
            clear = (y_end - y_first) / (li.h_count - 1) - li.h_phi
            if clear < smin_h - 1e-9:
                fits = False
                issues.append(f"Strzemiona poziome: odstęp w świetle {clear:.1f} mm < s_min {smin_h:.1f} mm "
                              f"(strefa {y_first:.0f}–{y_end:.0f} mm).")
        if y_first > y_lim:
            fits = False
            issues.append("Strzemiona poziome nie mieszczą się poniżej zbrojenia głównego.")
    v_pos: list[float] = []
    if li.v_count > 0:
        smin_v = s_min(li.v_phi, d_g, ps)
        x0 = cover.c_nom + li.v_phi / 2.0 + 25.0
        x1 = min(xi_A, sg.l_c - cover.c_nom - li.v_phi / 2.0)
        if x1 <= x0:
            fits = False
            issues.append("Brak miejsca na strzemiona pionowe między licem słupa a obciążeniem.")
        else:
            if li.v_count == 1:
                v_pos = [(x0 + x1) / 2.0]
            else:
                v_pos = [x0 + (x1 - x0) * k / (li.v_count - 1) for k in range(li.v_count)]
                clear = (x1 - x0) / (li.v_count - 1) - li.v_phi
                if clear < smin_v - 1e-9:
                    fits = False
                    issues.append(f"Strzemiona pionowe: odstęp w świetle {clear:.1f} mm < s_min {smin_v:.1f} mm.")
    return LinksLayout(li.h_phi, h_depths, li.v_phi, v_pos, li.i_phi, li.i_count, zone, issues, fits)


def links_crossing_strut(ll: LinksLayout, gm: GeometryModel, side: str, cover: CoverResult, xi_A: float,
                         y_A: float, xi_B: float, y_B: float) -> tuple[int, int]:
    """Liczba strzemion poziomych i pionowych przecinających oś krzyżulca A–B."""
    sg = gm.sides[side]
    nh = 0
    for dpt in ll.h_depths:
        y = -dpt
        if not (min(y_A, y_B) <= y <= max(y_A, y_B)):
            continue
        xi_strut = xi_B + (xi_A - xi_B) * (y - y_B) / (y_A - y_B) if abs(y_A - y_B) > 1e-9 else xi_A
        # zasięg strzemiona poziomego na głębokości dpt (wspornik o zmiennej wysokości)
        xi_max = sg.l_c - cover.c_nom
        if sg.h_e < sg.h_c and dpt + cover.c_nom > sg.h_e:
            # wyznacz ξ, dla którego wysokość = dpt + c_nom
            target = dpt + cover.c_nom
            if sg.l_c > sg.x_slope:
                t = (sg.h_c - target) / (sg.h_c - sg.h_e)
                xi_max = min(xi_max, sg.x_slope + t * (sg.l_c - sg.x_slope))
        if xi_max >= xi_strut:
            nh += 1
    nv = sum(1 for x in ll.v_positions if min(xi_B, xi_A) <= x <= max(xi_B, xi_A))
    return nh, nv


# ---------------------------------------------------------------------------
# Sprawdzenia konstrukcyjne
# ---------------------------------------------------------------------------
def cover_checks(cv: CoverResult, phi_main: float, combo: str = "") -> list[Check]:
    out = []
    sym = {"c_min,b": "otulina ze względu na przyczepność (tabl. 4.2)", "c_min,dur": "otulina ze względu na "
           "trwałość (tabl. 4.4N)", "Δc_dev": "odchyłka wykonawcza"}
    if cv.phi_link_outer > 0:
        out.append(make("COVER_LINK", "Konstrukcyjne", "Otulina nominalna strzemion",
                        "EN 1992-1-1 §4.4.1.1–4.4.1.3, wzory (4.1), (4.2), tabl. 4.2, 4.4N", Basis.NORMATIVE,
                        "c_nom = max{c_min,b; c_min,dur; 10 mm} + Δc_dev", sym,
                        f"ekspozycja {cv.exposure}, klasa {cv.structural_class}: c_min,dur = {mm(cv.c_min_dur)}; "
                        f"c_min,b = φ_s = {mm(cv.phi_link_outer)}; c_nom,req = {mm(cv.c_nom_req_link)}; "
                        f"przyjęto c_nom = {mm(cv.c_nom)}",
                        cv.c_nom_req_link, cv.c_nom, Kind.LENGTH, combo, "rebar:cover", E_label="c_nom,req",
                        R_label="c_nom"))
    out.append(make("COVER_MAIN", "Konstrukcyjne", "Otulina prętów zbrojenia głównego",
                    "EN 1992-1-1 §4.4.1.1–4.4.1.3, tabl. 4.2, 4.4N", Basis.NORMATIVE,
                    "c_main = c_nom + φ_s ≥ max{φ; c_min,dur; 10 mm} + Δc_dev", sym,
                    f"c_min,b = φ = {mm(phi_main)}; c_nom,req = {mm(cv.c_nom_req_main)}; c_main,góra = "
                    f"{mm(cv.c_top_main)}, c_main,bok = {mm(cv.c_side_main)}",
                    cv.c_nom_req_main, min(cv.c_top_main, cv.c_side_main), Kind.LENGTH, combo, "rebar:cover",
                    E_label="c_req", R_label="c_prov"))
    return out


def spacing_checks(ml: MainLayout, ll: LinksLayout | None, combo: str = "") -> list[Check]:
    out = []
    if ml.n >= 2:
        out.append(make("SPACING_MAIN", "Konstrukcyjne", "Odstęp w świetle prętów zbrojenia głównego",
                        "EN 1992-1-1 §8.2(2)", Basis.NORMATIVE, "a ≥ s_min = max{k₁·φ; d_g + k₂; 20 mm}",
                        {"a": "odstęp w świetle prętów w warstwie"},
                        f"a = {mm(ml.a_clear, 1)}; s_min = {mm(ml.s_min, 1)}",
                        ml.s_min, ml.a_clear, Kind.LENGTH, combo, "rebar:main", E_label="s_min", R_label="a"))
    else:
        out.append(make("SPACING_MAIN", "Konstrukcyjne", "Liczba prętów w warstwie", "Zasady konstruowania",
                        Basis.ENGINEERING, "n ≥ 2", {}, f"n = {ml.n}", 2.0, float(ml.n), Kind.RATIO, combo,
                        "rebar:main", recommendation=False))
    if ml.layers > 1:
        out.append(make("SPACING_LAYERS", "Konstrukcyjne", "Odstęp w świetle warstw zbrojenia głównego",
                        "EN 1992-1-1 §8.2(2), (3)", Basis.NORMATIVE, "s_v ≥ s_min", {},
                        f"s_v = {mm(ml.gap_v, 1)}; s_min = {mm(ml.s_min, 1)}", ml.s_min, ml.gap_v, Kind.LENGTH,
                        combo, "rebar:main", E_label="s_min", R_label="s_v"))
    if ll is not None:
        status = CheckStatus.OK if ll.fits else CheckStatus.FAIL
        out.append(make("SPACING_LINKS", "Konstrukcyjne", "Rozmieszczenie strzemion (mieszczenie się, odstępy)",
                        "EN 1992-1-1 §8.2(2)", Basis.NORMATIVE, "odstęp w świetle ≥ s_min; strzemiona w obrysie",
                        {}, "; ".join(ll.issues) if ll.issues else
                        f"{ll.desc_h()}; {ll.desc_v()} — rozmieszczenie wykonalne.",
                        None, None, Kind.NONE, combo, "rebar:links", status=status))
    return out


def vrdc(b: float, d: float, As: float, H: float, h_c: float, mats: Materials, ps: ParameterSet
         ) -> tuple[float, str]:
    """V_Rd,c wg 6.2.2(1), wzory (6.2.a), (6.2.b), (6.3N). H > 0 (rozciąganie) zmniejsza nośność."""
    c = mats.concrete
    k = min(1.0 + math.sqrt(200.0 / d), 2.0)
    rho = min(As / (b * d), 0.02)
    CRdc = ps.v("CRdc_num") / c.gamma_c
    k1 = ps.v("k1_shear")
    sigma_cp = -H / (b * h_c)  # ściskanie dodatnie
    sigma_cp = min(sigma_cp, ps.v("sigma_cp_max") * c.fcd)
    vmin = ps.v("vmin_coef") * k ** 1.5 * c.fck ** 0.5
    v1 = CRdc * k * (100.0 * rho * c.fck) ** (1.0 / 3.0) + k1 * sigma_cp
    v2 = vmin + k1 * sigma_cp
    V = max(v1, v2) * b * d
    V = max(V, 0.0)
    txt = (f"k = 1 + √(200/{n(d, 0)}) = {n(k, 3)}; ρ_l = {n(rho, 4)}; σ_cp = {n(sigma_cp, 3)} MPa; "
           f"V_Rd,c = max[{n(CRdc, 4)}·{n(k, 3)}·(100·{n(rho, 4)}·{n(c.fck, 0)})^(1/3) + {n(k1, 2)}·{n(sigma_cp, 3)}; "
           f"{n(vmin, 3)} + {n(k1, 2)}·{n(sigma_cp, 3)}]·{n(b, 0)}·{n(d, 0)} = {kN(V)}")
    return V, txt


def j3_link_checks(side: str, a_c: float, h_c: float, V: float, V_Rdc: float, vtxt: str, ml: MainLayout,
                   ll: LinksLayout, mats: Materials, ps: ParameterSet, combo: str) -> list[Check]:
    out = []
    k1 = ps.v("J3_k1")
    k2 = ps.v("J3_k2")
    fywd = mats.steel.link_fyd
    if a_c < 0.5 * h_c:
        As_lnk = ll.As_h + ll.As_i
        req = k1 * ml.As
        out.append(make(f"J32_{side}", "Zbrojenie poprzeczne", "Strzemiona poziome/ukośne przy a_c < 0,5·h_c",
                        "EN 1992-1-1 zał. J.3(2), rys. J.6a", Basis.INFORMATIVE,
                        "A_s,lnk ≥ k₁·A_s,main", {"k₁": "współczynnik (NDP, zalecane 0,25)",
                                                  "A_s,main": "pole zbrojenia głównego (przyjęte)"},
                        f"a_c = {mm(a_c)} < 0,5·{n(h_c, 0)} = {mm(0.5 * h_c)}; A_s,lnk,req = {n(k1, 2)}·"
                        f"{n(ml.As, 0)} = {mm2(req)}; A_s,lnk = {mm2(As_lnk)} ({ll.desc_h()}"
                        f"{'; ' + str(ll.i_count) + ' pr. ukośne' if ll.i_count else ''})",
                        req, As_lnk, Kind.AREA, combo, "rebar:links", E_label="A_s,lnk,req", R_label="A_s,lnk"))
    else:
        out.append(make(f"J32_{side}", "Zbrojenie poprzeczne", "Strzemiona poziome/ukośne (J.3(2))",
                        "EN 1992-1-1 zał. J.3(2)", Basis.INFORMATIVE, "warunek a_c < 0,5·h_c", {},
                        f"a_c = {mm(a_c)} ≥ 0,5·h_c = {mm(0.5 * h_c)} — wymaganie J.3(2) nie dotyczy.",
                        None, None, Kind.AREA, combo, "rebar:links", status=CheckStatus.NA))
    if a_c > 0.5 * h_c and V > V_Rdc:
        req = k2 * V / fywd
        out.append(make(f"J33_{side}", "Zbrojenie poprzeczne", "Strzemiona pionowe przy a_c > 0,5·h_c i F_Ed > V_Rd,c",
                        "EN 1992-1-1 zał. J.3(3), rys. J.6b; §6.2.2", Basis.INFORMATIVE,
                        "A_s,lnk ≥ k₂·F_Ed / f_yd", {"k₂": "współczynnik (NDP, zalecane 0,5)"},
                        f"{vtxt}; F_Ed = {kN(V)} > V_Rd,c → A_s,lnk,req = {n(k2, 2)}·{kN(V)}·10³/{n(fywd, 1)} = "
                        f"{mm2(req)}; A_s,lnk = {mm2(ll.As_v)} ({ll.desc_v()})",
                        req, ll.As_v, Kind.AREA, combo, "rebar:links", E_label="A_s,lnk,req", R_label="A_s,lnk"))
    else:
        why = (f"a_c = {mm(a_c)} ≤ 0,5·h_c" if a_c <= 0.5 * h_c else f"F_Ed = {kN(V)} ≤ V_Rd,c = {kN(V_Rdc)}")
        out.append(make(f"J33_{side}", "Zbrojenie poprzeczne", "Strzemiona pionowe (J.3(3))",
                        "EN 1992-1-1 zał. J.3(3); §6.2.2", Basis.INFORMATIVE, "a_c > 0,5·h_c i F_Ed > V_Rd,c", {},
                        f"{why} — wymaganie J.3(3) nie dotyczy. ({vtxt})",
                        None, None, Kind.AREA, combo, "rebar:links", status=CheckStatus.NA))
    return out


def min_max_checks(b: float, d: float, h_c: float, As: float, mats: Materials, ps: ParameterSet, combo: str = ""
                   ) -> list[Check]:
    c = mats.concrete
    As_min = max(ps.v("As_min_coef") * c.fctm / mats.steel.fyk * b * d, ps.v("As_min_abs") * b * d)
    As_max = ps.v("As_max_coef") * b * h_c
    return [
        make("AS_MIN", "Konstrukcyjne", "Minimalne zbrojenie główne (analogia do belek)",
             "EN 1992-1-1 §9.2.1.1(1), wzór (9.1N) — zastosowanie przez analogię", Basis.ENGINEERING,
             "A_s,min = max{0,26·f_ctm/f_yk·b·d; 0,0013·b·d}", {"b": "szerokość wspornika", "d": "wysokość użyteczna"},
             f"A_s,min = max{{0,26·{n(c.fctm, 1)}/{n(mats.steel.fyk, 0)}·{n(b, 0)}·{n(d, 0)}; 0,0013·{n(b, 0)}·{n(d, 0)}}}"
             f" = {mm2(As_min)}; A_s,prov = {mm2(As)}", As_min, As, Kind.AREA, combo, "rebar:main",
             recommendation=True, E_label="A_s,min", R_label="A_s,prov"),
        make("AS_MAX", "Konstrukcyjne", "Maksymalne zbrojenie główne (analogia do belek)",
             "EN 1992-1-1 §9.2.1.1(3) — zastosowanie przez analogię", Basis.ENGINEERING,
             "A_s ≤ A_s,max = 0,04·A_c", {}, f"A_s,max = 0,04·{n(b, 0)}·{n(h_c, 0)} = {mm2(As_max)}; A_s = {mm2(As)}",
             As, As_max, Kind.AREA, combo, "rebar:main", recommendation=True, E_label="A_s", R_label="A_s,max"),
    ]


# ---------------------------------------------------------------------------
# Dobór automatyczny
# ---------------------------------------------------------------------------
@dataclass
class MainCandidate:
    phi: float
    n: int
    layers: int
    As_req: float
    layout: MainLayout
    anchor_load: str
    ok: bool
    reason: str = ""


def design_main_bars(gm: GeometryModel, mi: MaterialsInput, ri: ReinforcementInput, ps: ParameterSet,
                     as_req_fn: Callable[[float], float],
                     anchor_ok_fn: Callable[[MainLayout, str], tuple[bool, str]],
                     log: list[str]) -> MainCandidate | None:
    """Dobór średnicy i liczby prętów zbrojenia głównego.

    ``as_req_fn(c_t)`` — wymagane A_s z modelu STM (tryb wymiarowania) dla danej osi cięgna;
    ``anchor_ok_fn(layout, anchor)`` — wykonalność zakotwień i odgięć dla układu."""
    li = ri.links
    best: MainCandidate | None = None
    load_options = [ri.main.anchor_load] + [a for a in ("loop", "welded_bar", "bend_down")
                                            if a != ri.main.anchor_load]
    for phi in sorted(ri.allowed_diameters):
        for layers in (1, 2):
            cv = cover_requirements(mi, ps, phi, li.h_phi, li.v_phi, li.v_count > 0, li.h_count > 0)
            probe = main_layout(gm.b, cv, phi, 2, layers, ri.main.layer_gap, mi.d_g, ps)
            try:
                As_req = as_req_fn(probe.c_t)
            except Exception as exc:  # noqa: BLE001 — niewykonalny model dla tej osi
                log.append(f"φ{phi:.0f}/{layers} warstwy: model niewykonalny ({exc}).")
                continue
            if not math.isfinite(As_req) or As_req <= 0:
                continue
            n_min = max(2, math.ceil(As_req / (layers * bar_area(phi)) - 1e-9))
            ml0 = main_layout(gm.b, cv, phi, n_min, layers, ri.main.layer_gap, mi.d_g, ps)
            if not ml0.fits:
                log.append(f"φ{phi:.0f}: {n_min}×{layers} — nie mieści się ({'; '.join(ml0.issues)}).")
                continue
            found = None
            reason = ""
            n_ = n_min
            # zwiększanie liczby prętów obniża σ_sd i wymaganą długość zakotwienia (8.3)
            while found is None:
                ml = main_layout(gm.b, cv, phi, n_, layers, ri.main.layer_gap, mi.d_g, ps)
                if not ml.fits:
                    break
                for anc in load_options:
                    if anc == "loop" and n_ % 2:
                        continue
                    ok, why = anchor_ok_fn(ml, anc)
                    if ok:
                        found = (ml, anc)
                        break
                    reason = why
                n_ += 1
            if found is None:
                log.append(f"φ{phi:.0f}/{layers} warstwy: brak wykonalnego zakotwienia/gięcia przy n ≥ {n_min} "
                           f"({reason}).")
                continue
            ml, chosen = found
            cand = MainCandidate(phi, ml.n, layers, As_req, ml, chosen, True)
            log.append(f"φ{phi:.0f}: {ml.n}×{layers} (A_s = {ml.As:.0f} ≥ {As_req:.0f} mm²), kotwienie: {chosen} — OK.")
            key = (ml.As, layers, ml.n * layers)
            if best is None or key < (best.layout.As, best.layers, best.n * best.layers):
                best = cand
    return best


def design_links(need_h_area: float, need_v_area: float, split_T: float, sin_t: float, cos_t: float,
                 fywd: float, li: LinksInput, room_h: int, room_v: int, log: list[str]) -> LinksInput:
    """Dobór strzemion: minimalne pole spełniające J.3 i warunek rozłupywania.

    room_h/room_v — maksymalna liczba strzemion mieszczących się w strefie (z wymogu s_min)."""
    out = LinksInput(**{**li.__dict__})
    out.auto = True
    best_v = (0, li.v_phi)
    if need_v_area > 0:
        cands = []
        for phi in LINK_DIAMETERS:
            k = math.ceil(need_v_area / (2.0 * bar_area(phi)) - 1e-9)
            if 1 <= k <= room_v:
                cands.append((k * 2.0 * bar_area(phi), k, phi))
        if cands:
            _, k, phi = min(cands)
            best_v = (k, phi)
        else:
            log.append("Strzemiona pionowe: brak układu mieszczącego się w strefie — wymagana zmiana geometrii.")
            best_v = (room_v, LINK_DIAMETERS[-1])
    out.v_count, out.v_phi = best_v
    R_v = 2.0 * out.v_count * bar_area(out.v_phi) * fywd * cos_t  # zakłada przecięcie krzyżulca (weryfikowane w analizie)
    need_h_split = max(split_T - R_v, 0.0) / (fywd * max(sin_t, 1e-6))
    need_h = max(need_h_area, need_h_split)
    cands = []
    for phi in LINK_DIAMETERS:
        k = max(li.min_constructive_h, math.ceil(need_h / (2.0 * bar_area(phi)) - 1e-9))
        if k <= room_h:
            cands.append((k * 2.0 * bar_area(phi), k, phi))
    if cands:
        _, k, phi = min(cands)
        out.h_count, out.h_phi = k, phi
    else:
        log.append("Strzemiona poziome: brak układu mieszczącego się w strefie — wymagana zmiana geometrii.")
        out.h_count, out.h_phi = room_h, LINK_DIAMETERS[-1]
    log.append(f"Dobór strzemion: poziome {out.h_count}×φ{out.h_phi:.0f} (wymagane A = {need_h:.0f} mm²), "
               f"pionowe {out.v_count}×φ{out.v_phi:.0f} (wymagane A = {need_v_area:.0f} mm²).")
    return out


# ---------------------------------------------------------------------------
# Zestawienie stali
# ---------------------------------------------------------------------------
@dataclass
class BarMark:
    mark: str
    description: str
    shape: str
    phi: float
    count: int
    length: float      # mm (jednej sztuki)
    grade: str

    @property
    def total_length(self) -> float:
        return self.count * self.length

    @property
    def mass(self) -> float:
        return self.total_length / 1000.0 * bar_unit_mass(self.phi)


def bar_schedule(gm: GeometryModel, geo_in: GeometryInput, ml: MainLayout, lls: dict[str, LinksLayout],
                 cv: CoverResult, mb: MainBarsInput, phi_m_load: float, phi_m_col: float, grade: str,
                 welded_phi: float | None) -> list[BarMark]:
    marks: list[BarMark] = []
    h2 = gm.h_col / 2.0
    c_col_in = gm.column_cover + gm.column_phi_link + gm.column_phi_long
    sides = list(gm.sides.keys())
    double = len(sides) == 2
    # długość części poziomej pręta głównego
    ends = {}
    for sd in sides:
        sg = gm.sides[sd]
        ends[sd] = sg.l_c - cv.c_nom
    front_leg = mb.front_leg if mb.front_leg is not None else max(5.0 * ml.phi, 100.0)
    col_leg = mb.column_leg if mb.column_leg is not None else max(5.0 * ml.phi, 100.0)
    if double:
        horiz = ends["R"] + ends["L"] + gm.h_col
        extra = 0.0
        shape = "pręt prosty ciągły"
    else:
        horiz = ends["R"] + gm.h_col - c_col_in
        extra = 0.0
        shape = "pręt"
        if mb.anchor_column == "bend_down":
            extra += col_leg + (math.pi / 4.0 - 1.0) * (phi_m_col + ml.phi)  # korekta łuku 90°
            shape += " z odgięciem w słupie"
    if mb.anchor_load == "bend_down":
        extra += (front_leg + (math.pi / 4.0 - 1.0) * (phi_m_load + ml.phi)) * (2 if double else 1)
        shape += ", odgięty w dół na końcu"
    if mb.anchor_load == "loop":
        n_u = ml.n // 2
        Lu = 2.0 * (horiz + extra) + math.pi * (phi_m_load + ml.phi) / 2.0 - 2.0 * (phi_m_load + ml.phi) / 2.0
        marks.append(BarMark("1", "Zbrojenie główne — pętle poziome (U)", "pętla U " + shape, ml.phi,
                             n_u * ml.layers, Lu, grade))
    else:
        marks.append(BarMark("1", "Zbrojenie główne (cięgno)", shape, ml.phi, ml.n * ml.layers, horiz + extra, grade))
    mk = 2
    if mb.anchor_load == "welded_bar":
        wp = welded_phi or ml.phi
        marks.append(BarMark(str(mk), "Pręt poprzeczny przyspawany (zakotwienie)", "pręt prosty", wp,
                             ml.layers * (2 if double else 1), gm.b - 2.0 * cv.c_nom, grade))
        mk += 1
    for sd in sides:
        ll = lls.get(sd)
        if ll is None:
            continue
        sg = gm.sides[sd]
        if ll.h_depths:
            lens = []
            for dpt in ll.h_depths:
                xi_max = sg.l_c - cv.c_nom
                target = dpt + cv.c_nom
                if sg.h_e < sg.h_c and target > sg.h_e and sg.l_c > sg.x_slope:
                    t = (sg.h_c - target) / (sg.h_c - sg.h_e)
                    xi_max = min(xi_max, sg.x_slope + t * (sg.l_c - sg.x_slope))
                Lx = xi_max + gm.h_col - c_col_in
                Lz = gm.b - 2.0 * cv.c_nom
                lens.append(2.0 * (Lx + Lz) + 2.0 * max(10.0 * ll.h_phi, 70.0))
            marks.append(BarMark(str(mk), f"Strzemiona poziome zamknięte ({'P' if sd == 'R' else 'L'})",
                                 "strzemię zamknięte poziome", ll.h_phi, len(ll.h_depths),
                                 sum(lens) / len(lens), grade))
            mk += 1
        if ll.v_positions:
            lens = []
            for xi in ll.v_positions:
                h = sg.depth_at(xi)
                lens.append(2.0 * ((h - 2.0 * cv.c_nom) + (gm.b - 2.0 * cv.c_nom)) + 2.0 * max(10.0 * ll.v_phi, 70.0))
            marks.append(BarMark(str(mk), f"Strzemiona pionowe zamknięte ({'P' if sd == 'R' else 'L'})",
                                 "strzemię zamknięte pionowe", ll.v_phi, len(ll.v_positions), sum(lens) / len(lens),
                                 grade))
            mk += 1
        if ll.i_count:
            L = math.sqrt(2.0) * sg.h_c + 2.0 * 40.0 * ll.i_phi
            marks.append(BarMark(str(mk), f"Pręty ukośne przy narożu wklęsłym ({'P' if sd == 'R' else 'L'})",
                                 "pręt prosty ukośny (orientacyjnie)", ll.i_phi, 2 * ll.i_count, L, grade))
            mk += 1
        if double and gm.sides.get("L") is not None and geo_in.left_mirror:
            pass
    return marks
