"""Silnik walidacji: kontrola danych wejściowych, automatyczne kontrole wyników
oraz rejestr statusu weryfikacji modułów obliczeniowych."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

from .core.model import Variant, Layout, side_input, active_sides
from .core.results import Message, Level, Check, CheckStatus
from .core.serialization import to_dict
from .core.units import Kind, DIMS
from .material_engine import CONCRETE_CLASSES, DUCTILITY_CLASSES
from .normative_parameters import EXPOSURE_GROUP, STRUCTURAL_CLASSES

# Status walidacji modułów: zweryfikowany | częściowo zweryfikowany | nieweryfikowany
MODULE_STATUS = {
    "stm_solver": ("zweryfikowany",
                   "Porównanie z rozwiązaniami analitycznymi kratownic (testy), kontrola residuów i rzędu macierzy, "
                   "zgodność z metodą sztywności dla układów niewyznaczalnych."),
    "stm_generator": ("zweryfikowany",
                      "Rozwiązanie zamknięte modelu J.5 porównywane w każdym obliczeniu z niezależnym rozwiązaniem "
                      "macierzowym; testy równowagi momentów wg wzoru F_td = F·a_c/z0 + H·(a_H+z0)/z0."),
    "material_engine": ("zweryfikowany",
                        "Wartości tabl. 3.1 kontrolowane wzorami tabl. 3.1 (f_ctm, f_ctk, E_cm) dla wszystkich klas."),
    "load_engine": ("zweryfikowany",
                    "Testy kombinacji (6.10), (6.10a/b), blokada podwójnego stosowania γ, import CSV/Excel."),
    "strut_checks": ("częściowo zweryfikowany",
                     "Zweryfikowane niezależnymi obliczeniami ręcznymi w testach; brak porównania z opublikowanym "
                     "przykładem obliczeniowym (do uzupełnienia przez użytkownika)."),
    "node_checks": ("częściowo zweryfikowany",
                    "Zweryfikowane niezależnymi obliczeniami ręcznymi w testach; brak porównania z opublikowanym "
                    "przykładem obliczeniowym."),
    "tie_checks": ("częściowo zweryfikowany", "Zweryfikowane obliczeniami ręcznymi w testach."),
    "anchorage_engine": ("częściowo zweryfikowany",
                         "Wzory (8.2)–(8.6), tabl. 8.2 zweryfikowane obliczeniami ręcznymi; interpretacja długości "
                         "dostępnej wg J.3(4) — do oceny projektanta."),
    "reinforcement_design": ("częściowo zweryfikowany",
                             "Otulina (4.4.1), odstępy (8.2), J.3(2)/(3) sprawdzone testami; zestawienie stali — "
                             "długości orientacyjne (bez dokładnej geometrii gięcia)."),
    "design_optimizer": ("częściowo zweryfikowany",
                         "Każdy wariant przechodzi pełną analizę; optymalizacja przeszukiwaniem siatki (deterministyczna)."),
    "report_engine": ("częściowo zweryfikowany", "Testy generowania PDF/Excel/CSV/JSON/DXF."),
    "visualization_engine": ("zweryfikowany",
                             "Automatyczna kontrola zgodności rysunku z modelem obliczeniowym (sygnatura geometrii, "
                             "współrzędne węzłów)."),
    "sls_crack_check": ("nieweryfikowany",
                        "Uproszczona kontrola rys wg tabl. 7.2N/7.3N bez korekt (7.6N)/(7.7N) — wyłącznie orientacyjnie."),
    "precast_bearing": ("nieweryfikowany",
                        "Tabl. 10.2 i f_Rd wg 10.9.5.2 — wartości do potwierdzenia; sprawdzenie nieaktywne bez potwierdzenia."),
}


def validate_input(v: Variant) -> list[Message]:
    """Kontrola poprawności danych wejściowych przed obliczeniami."""
    msgs: list[Message] = []

    def err(t, ref=""):
        msgs.append(Message(Level.ERROR, t, ref, "dane wejściowe"))

    def warn(t, ref=""):
        msgs.append(Message(Level.WARNING, t, ref, "dane wejściowe"))

    g = v.geometry
    if g.b <= 0:
        err("Szerokość wspornika b musi być dodatnia.", "geometry.b")
    col = g.column
    for name, val in (("h_col", col.h_col), ("b_col", col.b_col)):
        if val <= 0:
            err(f"Wymiar słupa {name} musi być dodatni.", f"column.{name}")
    if col.cover <= 0 or col.cover * 2 >= min(col.h_col, col.b_col):
        err("Nieprawidłowa otulina słupa.", "column.cover")
    if g.b > col.b_col + 1e-9:
        warn("Szerokość wspornika b większa od wymiaru słupa b_col — model zakłada przekazanie sił na słup "
             "o szerokości ≥ b; wymagana ocena projektanta.", "geometry.b")
    if g.layout not in (Layout.SINGLE, Layout.DOUBLE):
        err("Nieznany układ wspornika.")
    for sd in active_sides(g):
        s = side_input(g, sd)
        tag = f"[{sd}] "
        if s.l_c <= 0 or s.h_c <= 0 or s.h_e <= 0:
            err(tag + "Wymiary wspornika l_c, h_c, h_e muszą być dodatnie.", f"{sd}.l_c")
            continue
        if s.h_e > s.h_c + 1e-9:
            err(tag + "Wysokość na końcu h_e większa od wysokości przy licu h_c — geometria nieobsługiwana "
                      "(wspornik o wysokości rosnącej od słupa).", f"{sd}.h_e")
        if not (0 <= s.x_slope <= s.l_c):
            err(tag + "Początek skosu x_slope musi leżeć w przedziale [0; l_c].", f"{sd}.x_slope")
        if not (0 < s.a_c < s.l_c):
            err(tag + "Wysięg obciążenia a_c musi spełniać 0 < a_c < l_c.", f"{sd}.a_c")
        p = s.plate
        if p.length <= 0 or p.width <= 0 or p.thickness < 0:
            err(tag + "Wymiary płyty oporowej muszą być dodatnie.", f"{sd}.plate")
        xc = s.a_c + p.offset
        if xc - p.length / 2 < -1e-9 or xc + p.length / 2 > s.l_c + 1e-9:
            err(tag + "Płyta oporowa wychodzi poza obrys wspornika.", f"{sd}.plate")
        if p.width > g.b + 1e-9:
            err(tag + "Szerokość płyty b_p większa od szerokości wspornika b.", f"{sd}.plate.width")
        if s.d_user is not None and (s.d_user <= 0 or s.d_user >= s.h_c):
            err(tag + "Ręczna wysokość użyteczna d musi spełniać 0 < d < h_c.", f"{sd}.d_user")
        if s.a_H_user is not None and s.a_H_user < 0:
            err(tag + "Ramię a_H nie może być ujemne.", f"{sd}.a_H_user")
        if s.x_c_user is not None and s.x_c_user <= 0:
            err(tag + "Ręczne x_c musi być dodatnie.", f"{sd}.x_c_user")
        if s.z0_user is not None and s.z0_user <= 0:
            err(tag + "Ręczne z0 musi być dodatnie.", f"{sd}.z0_user")
        if s.h_c > 3.0 * s.l_c:
            warn(tag + "Bardzo duża wysokość względem wysięgu — sprawdź zakres stosowania modelu J.3.")
    m = v.materials
    if m.concrete not in CONCRETE_CLASSES:
        err(f"Nieznana klasa betonu {m.concrete}.", "materials.concrete")
    if m.steel_class not in DUCTILITY_CLASSES:
        err(f"Nieznana klasa ciągliwości {m.steel_class}.", "materials.steel_class")
    if m.exposure not in EXPOSURE_GROUP:
        err(f"Nieobsługiwana klasa ekspozycji {m.exposure}.", "materials.exposure")
    if m.structural_class not in STRUCTURAL_CLASSES:
        err(f"Nieznana klasa konstrukcji {m.structural_class}.", "materials.structural_class")
    if not (0 <= m.delta_c_dev <= 20):
        err("Δc_dev poza zakresem 0–20 mm.", "materials.delta_c_dev")
    elif m.delta_c_dev < 10:
        warn("Δc_dev < 10 mm — redukcja dopuszczalna tylko przy systemie zapewnienia jakości (4.4.1.3(3)).")
    if m.c_nom_user is not None and m.c_nom_user <= 0:
        err("Otulina nominalna musi być dodatnia.", "materials.c_nom_user")
    if not (4 <= m.d_g <= 63):
        err("Wymiar kruszywa d_g poza zakresem 4–63 mm.", "materials.d_g")
    mb = v.reinforcement.main
    if not mb.auto:
        if mb.phi <= 0 or mb.n_per_layer < 1 or mb.layers < 1:
            err("Nieprawidłowe parametry zbrojenia głównego.", "reinforcement.main")
        if mb.layers > 3:
            err("Program obsługuje maksymalnie 3 warstwy zbrojenia głównego.", "reinforcement.main.layers")
        if mb.anchor_load == "loop" and mb.n_per_layer % 2:
            err("Pętle poziome wymagają parzystej liczby prętów w warstwie.", "reinforcement.main.anchor_load")
    if mb.anchor_column == "continuous" and g.layout != Layout.DOUBLE:
        err("Zakotwienie 'pręt ciągły' dotyczy wyłącznie wsporników dwustronnych.", "reinforcement.main.anchor_column")
    li = v.reinforcement.links
    for name, val in (("h_phi", li.h_phi), ("v_phi", li.v_phi), ("i_phi", li.i_phi)):
        if val <= 0:
            err(f"Średnica strzemion {name} musi być dodatnia.", f"reinforcement.links.{name}")
    if li.h_count < 0 or li.v_count < 0 or li.i_count < 0:
        err("Liczba strzemion nie może być ujemna.")
    if not v.reinforcement.allowed_diameters:
        err("Brak dozwolonych średnic prętów dla doboru automatycznego.")
    st = v.stm
    if st.node_10pct and not st.node_10pct_justification.strip():
        warn("Zwiększenie σ_Rd,max o 10% (6.5.4(5)) wymaga uzasadnienia — NIE zastosowano.")
    if st.mode == "manual" and not st.manual.nodes:
        err("Tryb ręczny modelu STM: brak węzłów.", "stm.manual")
    for a in v.loads.actions:
        for name, val in (("V", a.V), ("H", a.H), ("M", a.M), ("e_x", a.e_x), ("e_y", a.e_y)):
            if not math.isfinite(val):
                err(f"Oddziaływanie '{a.name}': wartość {name} nieskończona.")
    return msgs


@dataclass
class ValidationItem:
    name: str
    ok: bool
    detail: str


def post_validate(result) -> list[ValidationItem]:
    """Automatyczne kontrole wyników (równowaga, jednostki, dodatniość, współczynniki)."""
    items: list[ValidationItem] = []
    # 1. równowaga statyczna każdego modelu
    for name, sr in result.stm.items():
        sol = sr.solution
        if sol.status == "error":
            continue
        ok = sol.equilibrium_ok
        items.append(ValidationItem(f"Równowaga statyczna — {name}", ok,
                                    f"max residuum węzłowe {sol.max_residual:.2e} N; ΣFx={sol.global_residual[0]:.2e} N, "
                                    f"ΣFy={sol.global_residual[1]:.2e} N, ΣM={sol.global_residual[2]:.2e} N·mm; "
                                    f"status: {sol.status}"))
        if sr.comparison:
            d = sr.comparison.get("max_rel_diff", 0.0)
            items.append(ValidationItem(f"Zgodność rozwiązania analitycznego i macierzowego — {name}", d <= 1e-6,
                                        f"maksymalna różnica względna {d:.2e}"))
    # 2. zgodność jednostek w sprawdzeniach
    bad_units = [c.id for c in result.checks if c.kind not in DIMS and c.kind not in (Kind.MASS,)]
    items.append(ValidationItem("Zgodność jednostek (E_d i R_d tej samej wielkości)", not bad_units,
                                "wszystkie sprawdzenia mają jednoznaczny wymiar" if not bad_units else str(bad_units)))
    # 3. dodatniość nośności
    neg = [c.id for c in result.checks if c.R_d is not None and c.R_d < 0]
    items.append(ValidationItem("Dodatniość nośności / wartości granicznych", not neg, ", ".join(neg) or "OK"))
    nan = [c.id for c in result.checks if c.eta is not None and (c.eta != c.eta)]
    items.append(ValidationItem("Brak wartości nieokreślonych (NaN)", not nan, ", ".join(nan) or "OK"))
    # 4. poprawność współczynników
    if result.materials is not None:
        c = result.materials.concrete
        coef_ok = (0 < c.nu_prime <= 1) and (c.gamma_c >= 1.0) and (result.materials.steel.gamma_s >= 1.0) \
            and (0 < c.alpha_cc <= 1.0)
        items.append(ValidationItem("Poprawność współczynników (0 < ν' ≤ 1, γ ≥ 1, α_cc ≤ 1)", coef_ok,
                                    f"ν'={c.nu_prime:.3f}, γ_c={c.gamma_c}, γ_s={result.materials.steel.gamma_s}, "
                                    f"α_cc={c.alpha_cc}"))
        cons = c.check_consistency()
        items.append(ValidationItem("Poprawność parametrów materiałowych (tabl. 3.1 vs wzory)", not cons,
                                    "; ".join(cons) or "zgodne"))
    # 5. poprawność geometrii
    if result.geometry is not None:
        gm = result.geometry
        ok = all(s.h_c > 0 and s.l_c > 0 and s.h_e > 0 for s in gm.sides.values()) and gm.b > 0
        items.append(ValidationItem("Poprawność geometrii (wymiary dodatnie, obrys zamknięty)", ok,
                                    f"{len(gm.outline())} wierzchołków obrysu"))
    return items


def hash_obj(obj) -> str:
    data = json.dumps(to_dict(obj), sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]


def result_fingerprint(result) -> str:
    """Odcisk wyników (do kontroli powtarzalności) — niezależny od czasu wykonania."""
    rows = []
    for c in sorted(result.checks, key=lambda c: c.id):
        rows.append([c.id, c.status.value, None if c.E_d is None else round(c.E_d, 6),
                     None if c.R_d is None else round(c.R_d, 6)])
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()[:16]
