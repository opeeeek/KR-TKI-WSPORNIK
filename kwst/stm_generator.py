"""Automatyczna generacja modelu Strut-and-Tie krótkiego wspornika (EN 1992-1-1 zał. J.3, rys. J.5).

Model (dla każdej strony wspornika):

* węzeł A (CCT) — przecięcie linii działania wypadkowej obciążenia (V, H, M)
  z osią cięgna; położenie: ξ_A = a_c + M/V + H·a_H/V (zapewnia dokładnie
  równowagę momentów z rys. J.5: F_td = F_Ed·a_c/z0 + H_Ed·(a_H + z0)/z0);
* węzeł B (CCC) — strefa ściskana przy licu słupa o wysokości x_c, węzeł
  hydrostatyczny (równe naprężenia na ściankach): środek na wysokości
  y = −(h_c − x_c/2), z0 = d − x_c/2;
  - tryb ``in_column`` (domyślny): pozioma ścianka węzła (przekazująca V do
    słupa) leży w słupie, ξ_B = −a_B/2, a_B = x_c·V/F_c;
  - tryb ``face`` (rys. J.5): ξ_B = 0 (węzeł na licu);
* węzeł C — zakotwienie cięgna w słupie (podpora modelu lokalnego);
* krzyżulec A–B, cięgno A–C.

Wysokość x_c jest parametrem swobodnym pola naprężeń (twierdzenie o dolnej
ocenie nośności). Program dobiera ją jawnie:

* ``optimal`` — minimalizacja maksymalnego wykorzystania (sprawdzenie) lub
  minimalnej siły w cięgnie przy spełnieniu warunków betonu (wymiarowanie),
  przy ograniczeniach geometrycznych i 1,0 ≤ tan θ ≤ 2,5 (J.3(1));
* ``node_limit`` — minimalne x_c z warunku σ_B = min(σ_Rd,max węzła CCC,
  σ_Rd,max krzyżulca);
* ``user`` — x_c lub z0 podane przez użytkownika.

Rozwiązanie zamknięte (analityczne) jest zawsze weryfikowane niezależnym
rozwiązaniem macierzowym (:mod:`kwst.stm_solver`).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .core.model import StmSettings, ManualStm
from .core.results import Message, Level
from .geometry_engine import GeometryModel, segment_inside, point_in_polygon
from .load_engine import SideActions, DesignCombination
from .material_engine import Materials, node_limits, strut_limit
from .normative_parameters import ParameterSet
from . import stm_solver as ss

Point = tuple[float, float]


@dataclass
class SideParams:
    side: str
    s: int
    V: float
    H_raw: float
    H: float                 # H użyte w modelu (po pominięciu korzystnej)
    M: float                 # Σ(M + V·e_x)
    e_y: float
    a_c: float
    a_H: float
    xi_A: float
    c_t: float               # odległość osi cięgna od górnej powierzchni
    d: float
    h_c: float
    u: float                 # wysokość strefy cięgna = 2·c_t
    a_p: float
    a_ef: float              # efektywna długość płyty (docisk)
    e_rel: float             # mimośród wypadkowej względem środka płyty
    t_A: float               # grubość krzyżulca/węzła przy A
    t_B: float               # grubość przy B
    node_b_mode: str
    sigma_strut: float
    sigma_strut_formula: str
    sigma_CCT: float
    sigma_CCC: float
    As_prov: float | None
    fyd: float
    tan_min: float
    tan_max: float
    x_lo: float
    x_hi_geom: float
    notes: list[str] = field(default_factory=list)
    T_anch: float | None = None   # nośność zakotwień cięgna (kryterium doboru x_c w trybie sprawdzenia)


@dataclass
class SideState:
    x_c: float
    z0: float
    xi_A: float
    y_A: float
    xi_B: float
    y_B: float
    a_B: float
    Fc: float
    T: float
    C: float
    theta: float      # rad
    w_A: float
    w_B: float
    sigma_bearing: float
    sigma_A: float    # naprężenie w krzyżulcu na ściance węzła A
    sigma_B: float    # naprężenie w węźle B (hydrostatyczny)
    eta: dict[str, float] = field(default_factory=dict)

    @property
    def tan_theta(self) -> float:
        return math.tan(self.theta)

    @property
    def theta_deg(self) -> float:
        return math.degrees(self.theta)

    def eta_concrete(self) -> float:
        return max(v for k, v in self.eta.items() if k not in ("tie", "anchorage"))

    def eta_max(self) -> float:
        return max(self.eta.values())


@dataclass
class SideModel:
    params: SideParams
    state: SideState
    search: dict
    feasible: bool
    infeasible_reason: str = ""


@dataclass
class NodeZone:
    id: str
    type: str
    center: Point
    polygon: list[Point]
    side: str = ""
    faces: list[dict] = field(default_factory=list)


@dataclass
class StrutGeom:
    id: str
    n1: str
    n2: str
    force: float          # N (ściskanie ujemne)
    w1: float
    w2: float
    t1: float
    t2: float
    polygon: list[Point]
    shape: str
    b_avail: float
    length: float
    theta_deg: float
    side: str = ""


@dataclass
class TieGeom:
    id: str
    n1: str
    n2: str
    force: float
    As_prov: float | None
    u: float
    polygon: list[Point]
    side: str = ""


@dataclass
class StmResult:
    combination: str
    model_type: str
    truss: ss.TrussModel
    solution: ss.TrussSolution
    sides: dict[str, SideModel]
    nodes: dict[str, NodeZone]
    struts: list[StrutGeom]
    ties: list[TieGeom]
    comparison: dict
    messages: list[Message] = field(default_factory=list)
    containment: dict[str, bool] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Parametry strony
# ---------------------------------------------------------------------------
def build_side_params(gm: GeometryModel, side: str, act: SideActions, mats: Materials, ps: ParameterSet,
                      st: StmSettings, c_t: float, As_prov: float | None,
                      a_H_user: float | None = None, d_user: float | None = None) -> SideParams:
    sg = gm.sides[side]
    notes: list[str] = []
    V = act.V
    H_raw = act.H
    H = H_raw
    if H_raw < 0 and st.neglect_favourable_H:
        H = 0.0
        notes.append("Siła H skierowana do słupa (korzystna) — pominięta w modelu (założenie bezpieczne).")
    d = sg.h_c - c_t
    if d_user is not None:
        d = d_user
    c_t_model = sg.h_c - d
    t_p = sg.plate.thickness if sg.plate.kind in ("steel_plate", "elastomer") else 0.0
    a_H = a_H_user if a_H_user is not None else c_t_model + t_p
    M = act.M
    xi_A = sg.a_c + (M / V if V > 0 else 0.0) + ((H * a_H / V) if (st.include_aH and V > 0) else 0.0)
    if not st.include_aH and H != 0:
        notes.append("Pominięto ramię a_H siły poziomej (decyzja użytkownika).")
    e_rel = (sg.a_c + (M / V if V > 0 else 0.0) + (H * t_p / V if V > 0 else 0.0)) - sg.plate.xi_center
    a_ef = sg.plate.length - 2.0 * abs(e_rel)
    e_y = act.e_y
    b_p_ef = sg.plate.width - 2.0 * abs(e_y)
    t_A = min(b_p_ef, gm.b - 2.0 * abs(e_y))
    t_B = gm.b - 2.0 * abs(e_y)
    if abs(e_y) > 1e-9:
        notes.append(f"Mimośród poprzeczny e_y = {e_y:.1f} mm: grubości efektywne t_A = {t_A:.0f} mm, "
                     f"t_B = {t_B:.0f} mm (b_ef = b − 2|e_y|) — założenie inżynierskie.")
    inc = bool(st.node_10pct and st.node_10pct_justification.strip())
    lim = node_limits(mats.concrete, ps, increase=inc)
    s_str, s_formula, _ = strut_limit(mats.concrete, ps, st.strut_limit)
    return SideParams(
        side=side, s=sg.s, V=V, H_raw=H_raw, H=H, M=M, e_y=e_y, a_c=sg.a_c, a_H=a_H, xi_A=xi_A,
        c_t=c_t_model, d=d, h_c=sg.h_c, u=2.0 * c_t_model, a_p=sg.plate.length, a_ef=a_ef, e_rel=e_rel,
        t_A=t_A, t_B=t_B, node_b_mode=st.node_b_position, sigma_strut=s_str, sigma_strut_formula=s_formula,
        sigma_CCT=lim["CCT"], sigma_CCC=lim["CCC"], As_prov=As_prov, fyd=mats.steel.fyd,
        tan_min=ps.v("J3_tan_min"), tan_max=ps.v("J3_tan_max"),
        x_lo=1.0, x_hi_geom=max(d - c_t_model, 1.0), notes=notes)


# ---------------------------------------------------------------------------
# Rozwiązanie zamknięte dla zadanego x_c
# ---------------------------------------------------------------------------
def evaluate(p: SideParams, x_c: float) -> SideState:
    z0 = p.d - x_c / 2.0
    V = p.V
    if z0 <= 0:
        raise ss.StmModelError("Ramię z0 ≤ 0 — strefa ściskana przekracza wysokość użyteczną.")
    if p.node_b_mode == "face":
        xi_B = 0.0
        if p.xi_A - xi_B <= 0:
            raise ss.StmModelError("Wypadkowa obciążenia w obrysie słupa (ξ_A ≤ ξ_B).")
        Fc = V * (p.xi_A - xi_B) / z0
        a_B = x_c * V / Fc
    else:
        disc = p.xi_A ** 2 + 2.0 * x_c * z0
        if p.xi_A <= -math.sqrt(max(disc, 0.0)) + 1e-9:
            raise ss.StmModelError("Wypadkowa obciążenia w obrysie słupa (ξ_A ≤ ξ_B).")
        Fc = V / (2.0 * z0) * (p.xi_A + math.sqrt(disc))
        a_B = x_c * V / Fc
        xi_B = -a_B / 2.0
        if p.xi_A - xi_B <= 0:
            raise ss.StmModelError("Wypadkowa obciążenia w obrysie słupa (ξ_A ≤ ξ_B).")
    T = Fc + p.H
    C = math.hypot(Fc, V)
    theta = math.atan2(V, Fc)
    w_A = p.a_ef * math.sin(theta) + p.u * math.cos(theta)
    w_B = math.hypot(x_c, a_B)
    sb = V / (p.a_ef * p.t_A) if p.a_ef > 0 and p.t_A > 0 else math.inf
    sA = C / (w_A * p.t_A) if w_A > 0 and p.t_A > 0 else math.inf
    sB = Fc / (x_c * p.t_B) if p.t_B > 0 else math.inf
    st = SideState(x_c, z0, p.xi_A, -p.c_t, xi_B, -(p.h_c - x_c / 2.0), a_B, Fc, T, C, theta, w_A, w_B, sb, sA, sB)
    st.eta = {
        "strut_A": sA / p.sigma_strut,
        "strut_B": sB / p.sigma_strut,
        "node_A_bearing": sb / p.sigma_CCT,
        "node_A_strut": sA / p.sigma_CCT,
        "node_B": sB / p.sigma_CCC,
    }
    if p.As_prov is not None:
        st.eta["tie"] = (T / (p.As_prov * p.fyd)) if p.As_prov > 0 else math.inf
        if p.T_anch is not None and math.isfinite(p.T_anch):
            st.eta["anchorage"] = T / p.T_anch if p.T_anch > 0 else math.inf
    return st


def _tan_at(p: SideParams, x: float) -> float:
    return evaluate(p, x).tan_theta


def _bisect(fn, lo: float, hi: float, it: int = 80, side: str = "mid") -> float:
    """Znajduje x, dla którego fn zmienia znak (fn(lo) i fn(hi) przeciwnych znaków).

    ``side='hi'`` zwraca koniec przedziału po stronie znaku fn(hi) (np. stronę
    spełniającą warunek), ``'mid'`` — środek końcowego przedziału."""
    flo = fn(lo)
    for _ in range(it):
        mid = 0.5 * (lo + hi)
        fm = fn(mid)
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return hi if side == "hi" else 0.5 * (lo + hi)


def feasible_interval(p: SideParams) -> tuple[float, float, str]:
    """Przedział x_c spełniający ograniczenia geometryczne i 1,0 ≤ tan θ ≤ 2,5."""
    lo, hi = p.x_lo, p.x_hi_geom
    if hi <= lo:
        return lo, hi, "Brak miejsca na strefę ściskaną węzła B (d − c_t ≤ 0)."
    t_lo, t_hi = _tan_at(p, lo), _tan_at(p, hi)  # tan θ maleje ze wzrostem x_c
    reason = ""
    a, b = lo, hi
    if t_hi > p.tan_max + 1e-12:
        reason = (f"Bardzo krótki wspornik: tan θ = {t_hi:.2f} > {p.tan_max} nawet przy maksymalnej strefie "
                  f"ściskanej — model J.3 niestosowalny wprost.")
        return lo, hi, reason
    if t_lo < p.tan_min - 1e-12:
        reason = (f"Wysięg zbyt duży: tan θ = {t_lo:.2f} < {p.tan_min} (a_c ≥ z0) — element nie jest krótkim "
                  "wspornikiem wg J.3; należy projektować jako belkę wspornikową (6.1, 6.2).")
        return lo, hi, reason
    if t_lo > p.tan_max:
        a = _bisect(lambda x: _tan_at(p, x) - p.tan_max, lo, hi)
    if t_hi < p.tan_min:
        b = _bisect(lambda x: _tan_at(p, x) - p.tan_min, lo, hi)
    return a, b, reason


def _golden(fn, a: float, b: float, it: int = 60) -> float:
    g = (math.sqrt(5) - 1) / 2
    c, d = b - g * (b - a), a + g * (b - a)
    fc, fd = fn(c), fn(d)
    for _ in range(it):
        if fc <= fd:
            b, d, fd = d, c, fc
            c = b - g * (b - a)
            fc = fn(c)
        else:
            a, c, fc = c, d, fd
            d = a + g * (b - a)
            fd = fn(d)
    return (a + b) / 2


def choose_xc(p: SideParams, st: StmSettings, design: bool, x_c_user: float | None = None,
              z0_user: float | None = None) -> tuple[float, dict, bool, str]:
    """Dobór wysokości strefy ściskanej x_c. Zwraca (x_c, opis, wykonalność, przyczyna)."""
    lo, hi, reason = feasible_interval(p)
    info: dict = {"x_min": lo, "x_max": hi, "mode": st.lever_arm}
    feasible = not reason
    if st.lever_arm == "user" and (x_c_user is not None or z0_user is not None):
        x = x_c_user if x_c_user is not None else 2.0 * (p.d - float(z0_user))
        info["method"] = "wartość użytkownika" + (" (z0)" if x_c_user is None else " (x_c)")
        ok = lo - 1e-6 <= x <= hi + 1e-6
        if not ok:
            return x, info, False, (reason or f"x_c = {x:.1f} mm poza przedziałem dopuszczalnym "
                                              f"[{lo:.1f}; {hi:.1f}] mm (geometria / tan θ wg J.3(1)).")
        return x, info, feasible, reason
    if not feasible:
        # model poza zakresem J.3 — pole naprężeń dobrane wyłącznie informacyjnie (min. wykorzystanie),
        # wynik oznaczony jako niestosowalny
        lo_g, hi_g = p.x_lo, p.x_hi_geom
        obj = (lambda x: evaluate(p, x).eta_max()) if (p.As_prov is not None and not design) else \
            (lambda x: evaluate(p, x).eta_concrete())
        xs = [lo_g + (hi_g - lo_g) * i / 47 for i in range(48)]
        k = min(range(48), key=lambda i: obj(xs[i]))
        x = _golden(obj, xs[max(k - 1, 0)], xs[min(k + 1, 47)])
        if obj(x) > obj(xs[k]):
            x = xs[k]
        info["method"] = "model poza zakresem J.3 — pole naprężeń informacyjne (min. wykorzystanie)"
        return x, info, False, reason
    if st.lever_arm == "node_limit":
        target = min(p.sigma_CCC, p.sigma_strut)
        f = lambda x: evaluate(p, x).sigma_B - target
        if f(lo) <= 0:
            x = lo
        elif f(hi) > 0:
            x = hi
        else:
            x = _bisect(f, lo, hi, side="hi")
        info["method"] = "σ_B = min(σ_Rd,max CCC; σ_Rd,max krzyżulca)"
        return x, info, True, ""
    n = 64
    xs = [lo + (hi - lo) * i / (n - 1) for i in range(n)]
    if design or p.As_prov is None:
        etas = [evaluate(p, x).eta_concrete() for x in xs]
        k = next((i for i, e in enumerate(etas) if e <= 1.0), None)
        if k is None:
            x = _golden(lambda x: evaluate(p, x).eta_concrete(), lo, hi)
            info["method"] = "min. wykorzystanie betonu (brak pola spełniającego warunki)"
        elif k == 0:
            x = lo
            info["method"] = "min. siła w cięgnie przy η_beton ≤ 1"
        else:
            x = _bisect(lambda x: evaluate(p, x).eta_concrete() - 1.0, xs[k - 1], xs[k], side="hi")
            if evaluate(p, x).eta_concrete() > 1.0:
                x = xs[k]
            info["method"] = "min. siła w cięgnie przy η_beton ≤ 1"
        return x, info, True, ""
    etas = [evaluate(p, x).eta_max() for x in xs]
    k = min(range(n), key=lambda i: etas[i])
    a = xs[max(k - 1, 0)]
    b = xs[min(k + 1, n - 1)]
    x = _golden(lambda x: evaluate(p, x).eta_max(), a, b)
    if evaluate(p, x).eta_max() > etas[k]:
        x = xs[k]
    info["method"] = "minimalizacja maksymalnego wykorzystania (dolne oszacowanie nośności)"
    return x, info, True, ""


# ---------------------------------------------------------------------------
# Budowa modelu kratownicowego i geometrii stref
# ---------------------------------------------------------------------------
def _rect(x0, x1, y0, y1) -> list[Point]:
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _strut_polygon(A: Point, B: Point, wA: float, wB: float) -> list[Point]:
    dx, dy = B[0] - A[0], B[1] - A[1]
    L = math.hypot(dx, dy)
    nx, ny = -dy / L, dx / L
    return [(A[0] + nx * wA / 2, A[1] + ny * wA / 2), (B[0] + nx * wB / 2, B[1] + ny * wB / 2),
            (B[0] - nx * wB / 2, B[1] - ny * wB / 2), (A[0] - nx * wA / 2, A[1] - ny * wA / 2)]


def splitting_geometry(gm: GeometryModel, A: Point, B: Point) -> float:
    """Dostępna szerokość rozchodzenia się krzyżulca w połowie długości (prostopadle do osi)."""
    mx, my = (A[0] + B[0]) / 2, (A[1] + B[1]) / 2
    dx, dy = B[0] - A[0], B[1] - A[1]
    L = math.hypot(dx, dy)
    nx, ny = -dy / L, dx / L
    poly = gm.outline()
    d1 = gm.ray_distance((mx, my), (nx, ny))
    d2 = gm.ray_distance((mx, my), (-nx, -ny))
    if not point_in_polygon((mx, my), poly):
        return 0.0
    return d1 + d2


def build_corbel_model(gm: GeometryModel, combo: DesignCombination, mats: Materials, ps: ParameterSet,
                       st: StmSettings, c_t: float, As_prov: float | None, design: bool,
                       side_inputs: dict | None = None) -> StmResult:
    """Buduje i rozwiązuje model STM wspornika (jedno- lub dwustronnego) dla kombinacji."""
    msgs: list[Message] = []
    side_inputs = side_inputs or {}
    truss = ss.TrussModel()
    sides: dict[str, SideModel] = {}
    nodes: dict[str, NodeZone] = {}
    struts: list[StrutGeom] = []
    ties: list[TieGeom] = []
    h2 = gm.h_col / 2.0
    double = len(gm.sides) == 2
    # węzeł C — zakotwienie cięgna w słupie
    if double:
        xC = 0.0
    else:
        xC = -(h2 - gm.column_cover - gm.column_phi_link - gm.column_phi_long / 2.0)
    yC = -c_t
    active = []
    for sd, sg in gm.sides.items():
        act = combo.sides.get(sd)
        if act is None:
            continue
        if act.V < -1e-6:
            msgs.append(Message(Level.ERROR, f"Strona {sd}: siła V < 0 (odrywanie) — model wspornika krótkiego "
                                             "J.3 nie obejmuje tego przypadku.", f"side:{sd}"))
            continue
        if act.V <= 1e-6:
            if abs(act.H) > 1e-6:
                msgs.append(Message(Level.WARNING, f"Strona {sd}: brak siły pionowej, H ≠ 0 — siła pozioma "
                                                   "przenoszona bezpośrednio przez cięgno (T = H).", f"side:{sd}"))
            continue
        si = side_inputs.get(sd, {})
        p = build_side_params(gm, sd, act, mats, ps, st, c_t, As_prov, si.get("a_H_user"), si.get("d_user"))
        p.T_anch = si.get("T_anch")
        if p.a_ef <= 0:
            msgs.append(Message(Level.ERROR, f"Strona {sd}: wypadkowa obciążenia poza płytą oporową "
                                             f"(e = {p.e_rel:.1f} mm, a_p = {p.a_p:.0f} mm).", f"side:{sd}"))
            continue
        if p.t_A <= 0 or p.t_B <= 0:
            msgs.append(Message(Level.ERROR, f"Strona {sd}: mimośród poprzeczny e_y zbyt duży (b_ef ≤ 0).",
                                f"side:{sd}"))
            continue
        try:
            x_c, info, feas, reason = choose_xc(p, st, design, si.get("x_c_user"), si.get("z0_user"))
            state = evaluate(p, x_c)
        except ss.StmModelError as exc:
            msgs.append(Message(Level.ERROR, f"Strona {sd}: {exc}", f"side:{sd}"))
            continue
        sides[sd] = SideModel(p, state, info, feas, reason)
        active.append(sd)
    if not active:
        empty = ss.TrussSolution({}, {}, "error", "none", 0, 0, 0, 0, {}, 0.0, (0.0, 0.0, 0.0), 0.0,
                                 ["Brak aktywnych stron modelu."])
        return StmResult(combo.name, "J.3", truss, empty, sides, nodes, struts, ties, {}, msgs)
    truss.nodes.append(ss.TrussNode("C", xC, yC))
    truss.supports.append(ss.TrussSupport("C", True, True))
    for sd in active:
        sm = sides[sd]
        p, s_ = sm.params, sm.state
        sg = gm.sides[sd]
        A = sg.g(s_.xi_A, s_.y_A)
        B = sg.g(s_.xi_B, s_.y_B)
        nA, nB = f"A{sd}", f"B{sd}"
        truss.nodes += [ss.TrussNode(nA, *A), ss.TrussNode(nB, *B)]
        truss.members += [ss.TrussMember(f"S{sd}", nA, nB, "strut"), ss.TrussMember(f"T{sd}", nA, "C", "tie")]
        truss.supports.append(ss.TrussSupport(nB, True, True))
        truss.loads.append(ss.TrussLoad(nA, sg.s * p.H, -p.V))
    sol = ss.solve(truss)
    comp: dict = {"max_rel_diff": 0.0, "items": []}
    for sd in active:
        sm = sides[sd]
        p, s_ = sm.params, sm.state
        sg = gm.sides[sd]
        T_m = sol.forces.get(f"T{sd}", math.nan)
        C_m = -sol.forces.get(f"S{sd}", math.nan)
        for name, a, b in (("T", s_.T, T_m), ("C", s_.C, C_m)):
            rel = abs(a - b) / max(abs(a), 1.0)
            comp["items"].append((f"{name}{sd}", a, b, rel))
            comp["max_rel_diff"] = max(comp["max_rel_diff"], rel)
        A = sg.g(s_.xi_A, s_.y_A)
        B = sg.g(s_.xi_B, s_.y_B)
        nA, nB = f"A{sd}", f"B{sd}"
        # strefa węzła A: pod płytą, wysokość u
        xa0, xa1 = sorted((sg.g(s_.xi_A - p.a_ef / 2, 0)[0], sg.g(s_.xi_A + p.a_ef / 2, 0)[0]))
        nodes[nA] = NodeZone(nA, "CCT", A, _rect(xa0, xa1, -p.u, 0.0), sd, faces=[
            {"name": "ścianka docisku (płyta)", "F": p.V, "length": p.a_ef, "t": p.t_A, "sigma": s_.sigma_bearing},
            {"name": "ścianka krzyżulca", "F": s_.C, "length": s_.w_A, "t": p.t_A, "sigma": s_.sigma_A},
        ])
        xb0, xb1 = sorted((sg.g(s_.xi_B - s_.a_B / 2, 0)[0], sg.g(s_.xi_B + s_.a_B / 2, 0)[0]))
        nodes[nB] = NodeZone(nB, "CCC", B, _rect(xb0, xb1, -p.h_c, -p.h_c + s_.x_c), sd, faces=[
            {"name": "ścianka pionowa (F_c)", "F": s_.Fc, "length": s_.x_c, "t": p.t_B, "sigma": s_.sigma_B},
            {"name": "ścianka pozioma (V)", "F": p.V, "length": s_.a_B, "t": p.t_B, "sigma": p.V / (s_.a_B * p.t_B)},
            {"name": "ścianka krzyżulca", "F": s_.C, "length": s_.w_B, "t": p.t_B, "sigma": s_.C / (s_.w_B * p.t_B)},
        ])
        L = math.hypot(B[0] - A[0], B[1] - A[1])
        b_av = splitting_geometry(gm, A, B)
        shape = "butelkowy" if b_av > 1.2 * max(s_.w_A, s_.w_B) else "pryzmatyczny"
        struts.append(StrutGeom(f"S{sd}", nA, nB, -s_.C, s_.w_A, s_.w_B, p.t_A, p.t_B,
                                _strut_polygon(A, B, s_.w_A, s_.w_B), shape, b_av, L, s_.theta_deg, sd))
        xt0, xt1 = sorted((A[0], xC))
        ties.append(TieGeom(f"T{sd}", nA, "C", s_.T, As_prov, p.u, _rect(xt0, xt1, -p.u, 0.0), sd))
        # kontrola mieszczenia się krzyżulca w obrysie (krawędzie boczne między węzłami)
        poly = _strut_polygon(A, B, s_.w_A, s_.w_B)
        outline = gm.outline()
        e1 = (poly[0], poly[1])
        e2 = (poly[3], poly[2])
        def edge_ok(e, t0, t1):
            (ax, ay), (bx, by) = e
            pa = (ax + t0 * (bx - ax), ay + t0 * (by - ay))
            pb = (ax + t1 * (bx - ax), ay + t1 * (by - ay))
            return segment_inside(pa, pb, outline, 41, tol=1.0)
        lower = e1 if sg.s > 0 else e2
        upper = e2 if sg.s > 0 else e1
        res_c = {
            "strut_lower": edge_ok(lower, 0.05, 0.95),
            "strut_upper": edge_ok(upper, 0.25, 0.95),
            "node_A": all(point_in_polygon(q, outline, 1.0) for q in nodes[nA].polygon),
            "node_B": all(point_in_polygon(q, outline, 1.0) for q in nodes[nB].polygon),
        }
        for k, v in res_c.items():
            sm_key = f"{k}_{sd}"
            # wynik zapisywany w StmResult.containment
            comp.setdefault("containment", {})[sm_key] = v
    nodes["C"] = NodeZone("C", "kotwienie (słup)", (xC, yC), [], "", faces=[])
    res = StmResult(combo.name, "J.3 dwustronny" if double else "J.3 jednostronny", truss, sol, sides, nodes,
                    struts, ties, comp, msgs, containment=comp.get("containment", {}))
    if comp["max_rel_diff"] > 1e-6:
        res.messages.append(Message(Level.ERROR,
                                    f"Niezgodność rozwiązania analitycznego i macierzowego "
                                    f"({comp['max_rel_diff']:.2e}) — model odrzucony."))
    return res


# ---------------------------------------------------------------------------
# Model ręczny
# ---------------------------------------------------------------------------
def build_manual_model(man: ManualStm) -> ss.TrussModel:
    t = ss.TrussModel()
    t.nodes = [ss.TrussNode(n.id, n.x, n.y) for n in man.nodes]
    t.members = []
    for m in man.members:
        EA = None
        if m.kind == "strut":
            EA = 30000.0 * max(m.width, 1.0) * max(m.thickness, 1.0)
        elif m.As > 0:
            EA = 200000.0 * m.As
        t.members.append(ss.TrussMember(m.id, m.n1, m.n2, m.kind, EA))
    t.supports = [ss.TrussSupport(s.node, s.ux, s.uy) for s in man.supports]
    t.loads = [ss.TrussLoad(ld.node, ld.Fx, ld.Fy) for ld in man.loads]
    return t


def manual_from_result(res: StmResult, b: float) -> ManualStm:
    """Kopiuje automatyczny model do edytora ręcznego (punkt wyjścia do modyfikacji)."""
    from .core.model import ManualNode, ManualMember, ManualSupport, ManualLoad
    man = ManualStm()
    for n in res.truss.nodes:
        man.nodes.append(ManualNode(n.id, round(n.x, 3), round(n.y, 3)))
    sgeo = {s.id: s for s in res.struts}
    tgeo = {t.id: t for t in res.ties}
    for m in res.truss.members:
        if m.id in sgeo:
            sg = sgeo[m.id]
            man.members.append(ManualMember(m.id, m.n1, m.n2, "strut", round(min(sg.w1, sg.w2), 1),
                                            round(min(sg.t1, sg.t2), 1), 0.0))
        else:
            tg = tgeo.get(m.id)
            man.members.append(ManualMember(m.id, m.n1, m.n2, "tie", 0.0, b, round(tg.As_prov or 0.0, 1)))
    for s in res.truss.supports:
        man.supports.append(ManualSupport(s.node, s.ux, s.uy, 100.0))
    for ld in res.truss.loads:
        man.loads.append(ManualLoad(ld.node, ld.Fx, ld.Fy))
    return man
