"""Optymalizacja wspornika — deterministyczne przeszukiwanie siatki wariantów.

Zmienne: wysokość przy licu h_c (h_e skalowane proporcjonalnie), długość wysięgu l_c
(a_c bez zmian — położenie oparcia wynika z elementu podpieranego), szerokość b, klasa
betonu, dopuszczalne średnice prętów głównych (dobór automatyczny zbrojenia).

Każdy wariant przechodzi PEŁNĄ analizę (:func:`kwst.analysis.run_analysis`). Wariant jest
dopuszczalny wyłącznie, gdy nie ma błędów krytycznych, niespełnionych sprawdzeń ani
przekroczenia zakresu modelu (werdykt PASS_SCOPE lub CONDITIONAL — ten drugi wyłącznie z
powodu niepotwierdzonych NDP, identycznie jak wariant bazowy).
"""
from __future__ import annotations

import copy
import itertools
from dataclasses import dataclass, field
from typing import Callable

from .analysis import run_analysis
from .core.model import Variant
from .core.results import CheckStatus

OBJECTIVES = {
    "steel": "Minimalne zużycie stali [kg]",
    "concrete": "Minimalna objętość betonu wspornika [m³]",
    "height": "Minimalna wysokość wspornika h_c [mm]",
    "length": "Minimalna długość wysięgu l_c [mm]",
    "cost": "Minimalny koszt materiałów [zł]",
    "eta": "Najmniejsze maksymalne wykorzystanie η_max",
}

DEFAULT_CONCRETE_PRICE = {  # zł/m³ — wartości przykładowe, edytowalne przez użytkownika
    "C20/25": 380.0, "C25/30": 400.0, "C30/37": 430.0, "C35/45": 460.0, "C40/50": 500.0, "C45/55": 540.0,
    "C50/60": 590.0,
}


@dataclass
class OptSettings:
    objective: str = "steel"
    h_c: tuple[float, float, float] | None = None      # (min, max, krok) [mm]
    l_c: tuple[float, float, float] | None = None
    b: tuple[float, float, float] | None = None
    concretes: list[str] = field(default_factory=lambda: ["C25/30", "C30/37", "C35/45", "C40/50"])
    diameters: list[float] = field(default_factory=lambda: [12.0, 14.0, 16.0, 20.0, 25.0])
    steel_price: float = 5.5           # zł/kg
    concrete_price: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_CONCRETE_PRICE))
    max_variants: int = 400


@dataclass
class OptVariant:
    variant: Variant
    h_c: float
    h_e: float
    l_c: float
    b: float
    concrete: str
    main: str
    links: str
    steel_kg: float
    concrete_m3: float
    cost: float
    eta_max: float
    verdict: str
    feasible: bool
    reason: str
    objective: float = 0.0


def _rng(t: tuple[float, float, float] | None, base: float) -> list[float]:
    if t is None:
        return [base]
    lo, hi, st = t
    if st <= 0 or hi < lo:
        return [base]
    n = int(round((hi - lo) / st)) + 1
    return [round(lo + i * st, 6) for i in range(n)]


def evaluate(v: Variant, s: OptSettings) -> OptVariant:
    r = run_analysis(v)
    g = v.geometry
    sg = g.right
    vol = 0.0
    if r.geometry is not None:
        vol = sum(sd.volume_per_b for sd in r.geometry.sides.values()) * g.b / 1e9
    steel = sum(b.mass for b in r.schedule)
    cost = steel * s.steel_price + vol * s.concrete_price.get(v.materials.concrete, 450.0)
    crit = r.critical()
    eta = crit.eta if crit and crit.eta is not None else float("inf")
    fails = [c.id for c in r.checks if c.status == CheckStatus.FAIL]
    code = r.verdict.code if r.verdict else "BLOCKED"
    feasible = code in ("PASS_SCOPE", "CONDITIONAL") and not fails and not r.errors
    reason = "" if feasible else (r.errors[0].text if r.errors else (", ".join(fails[:4]) or r.verdict.title))
    main = r.main.desc() if r.main else "—"
    links = "; ".join(f"{ll.desc_h()}, {ll.desc_v()}" for ll in r.links.values()) if r.links else "—"
    return OptVariant(v, sg.h_c, sg.h_e, sg.l_c, g.b, v.materials.concrete, main, links, steel, vol, cost, eta, code,
                      feasible, reason)


def _objective(o: OptVariant, key: str) -> float:
    return {"steel": o.steel_kg, "concrete": o.concrete_m3, "height": o.h_c, "length": o.l_c, "cost": o.cost,
            "eta": o.eta_max}[key]


def optimize(base: Variant, s: OptSettings, progress: Callable[[int, int], None] | None = None,
             cancelled: Callable[[], bool] | None = None) -> list[OptVariant]:
    g = base.geometry
    hcs = _rng(s.h_c, g.right.h_c)
    lcs = _rng(s.l_c, g.right.l_c)
    bs = _rng(s.b, g.b)
    concretes = s.concretes or [base.materials.concrete]
    grid = list(itertools.product(hcs, lcs, bs, concretes))[: s.max_variants]
    out: list[OptVariant] = []
    for k, (hc, lc, b, cls) in enumerate(grid):
        if cancelled and cancelled():
            break
        v = copy.deepcopy(base)
        ratio = g.right.h_e / g.right.h_c
        v.name = f"{base.name} | h_c={hc:.0f}, l_c={lc:.0f}, b={b:.0f}, {cls}"
        v.geometry.right.h_c = hc
        v.geometry.right.h_e = round(hc * ratio, 1)
        v.geometry.right.x_slope = min(v.geometry.right.x_slope, lc)
        v.geometry.right.l_c = lc
        v.geometry.b = b
        v.geometry.right.plate.width = min(v.geometry.right.plate.width, b)
        v.materials.concrete = cls
        v.reinforcement.main.auto = True
        v.reinforcement.links.auto = True
        v.reinforcement.allowed_diameters = list(s.diameters) or v.reinforcement.allowed_diameters
        v.geometry.right.d_user = None
        v.geometry.right.x_c_user = None
        v.geometry.right.z0_user = None
        o = evaluate(v, s)
        o.objective = _objective(o, s.objective)
        out.append(o)
        if progress:
            progress(k + 1, len(grid))
    out.sort(key=lambda o: (not o.feasible, o.objective, o.eta_max))
    return out
