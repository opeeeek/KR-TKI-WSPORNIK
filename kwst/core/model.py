"""Model danych wejściowych projektu (jawnie typowane dataclasses).

Wszystkie wartości liczbowe w jednostkach bazowych: N, mm, MPa, N·mm.

Konwencja znaków obciążeń (dla każdej strony wspornika osobno):

* ``V`` — siła pionowa, dodatnia w dół (obciążenie grawitacyjne);
* ``H`` — siła pozioma, dodatnia w kierunku OD słupa (rozciągająca wspornik);
* ``M`` — moment w miejscu oparcia, dodatni gdy przesuwa wypadkową pionową
  OD słupa (zwiększa ramię a_c);
* ``e_x`` — dodatkowy mimośród podłużny siły V względem a_c (+ od słupa);
* ``e_y`` — mimośród poprzeczny siły V względem osi wspornika (szerokość b).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

SCHEMA_VERSION = 1


class Layout(str, Enum):
    SINGLE = "single"     # wspornik jednostronny
    DOUBLE = "double"     # wsporniki dwustronne


class Construction(str, Enum):
    MONOLITHIC = "monolithic"
    PRECAST = "precast"


# ---------------------------------------------------------------------------
# Geometria
# ---------------------------------------------------------------------------
@dataclass
class ColumnInput:
    h_col: float = 400.0       # wymiar słupa w płaszczyźnie wspornika [mm]
    b_col: float = 400.0       # wymiar słupa prostopadle do płaszczyzny [mm]
    above: float = 400.0       # długość słupa nad wspornikiem (rysunek) [mm]
    below: float = 700.0       # długość słupa pod wspornikiem (rysunek; ogranicza ramię zakotwienia) [mm]
    cover: float = 30.0        # otulina nominalna słupa (do strzemion) [mm]
    phi_long: float = 20.0     # średnica prętów podłużnych słupa [mm]
    phi_link: float = 8.0      # średnica strzemion słupa [mm]
    N_Ed: float = 0.0          # siła osiowa w słupie (informacyjnie) [N]


@dataclass
class PlateInput:
    kind: str = "steel_plate"   # steel_plate | elastomer | direct
    length: float = 150.0       # a_p — wymiar wzdłuż wysięgu [mm]
    width: float = 300.0        # b_p — wymiar w poprzek wspornika [mm]
    thickness: float = 20.0     # t_p [mm]
    offset: float = 0.0         # przesunięcie środka płyty względem linii a_c (+ od słupa) [mm]


@dataclass
class CorbelSideInput:
    side: str = "R"
    l_c: float = 400.0          # długość wysięgu wspornika od lica słupa [mm]
    h_c: float = 550.0          # wysokość wspornika przy licu słupa [mm]
    h_e: float = 350.0          # wysokość wspornika na końcu [mm]
    x_slope: float = 0.0        # początek skosu dolnej krawędzi (od lica) [mm]
    a_c: float = 250.0          # wysięg obciążenia: lico słupa → linia działania V [mm]
    plate: PlateInput = field(default_factory=PlateInput)
    a_H_user: Optional[float] = None   # ramię siły H nad osią cięgna (None = automatycznie)
    d_user: Optional[float] = None     # ręczna korekta wysokości użytecznej d
    x_c_user: Optional[float] = None   # ręczna wysokość strefy ściskanej węzła B
    z0_user: Optional[float] = None    # ręczne ramię sił wewnętrznych z0


@dataclass
class PrecastInput:
    """Dane połączenia prefabrykowanego (EN 1992-1-1 §10.9.5)."""
    support_type: str = "concentrated"   # concentrated | line | ribbed (tabl. 10.2)
    dry_connection: bool = True          # oparcie "na sucho" → f_Rd = 0,4·f_cd
    f_bed: float = 0.0                   # wytrzymałość podlewki (połączenia nie-suche) [MPa]
    restraint_considered: bool = False   # projektant uwzględnił siły od więzów (skurcz, pełzanie, temperatura)


@dataclass
class GeometryInput:
    layout: Layout = Layout.SINGLE
    construction: Construction = Construction.MONOLITHIC
    b: float = 400.0                    # szerokość wspornika [mm]
    column: ColumnInput = field(default_factory=ColumnInput)
    right: CorbelSideInput = field(default_factory=CorbelSideInput)
    left: CorbelSideInput = field(default_factory=lambda: CorbelSideInput(side="L"))
    left_mirror: bool = True            # lewy wspornik = lustrzane odbicie prawego
    precast: PrecastInput = field(default_factory=PrecastInput)


# ---------------------------------------------------------------------------
# Materiały i trwałość
# ---------------------------------------------------------------------------
@dataclass
class MaterialsInput:
    concrete: str = "C30/37"
    steel_name: str = "B500SP"
    steel_fyk: float = 500.0
    steel_class: str = "C"            # klasa ciągliwości A/B/C (zał. C)
    link_fyk: float = 500.0
    Es: float = 200000.0
    d_g: float = 16.0                 # maksymalny wymiar kruszywa [mm]
    exposure: str = "XC1"
    structural_class: str = "S4"
    delta_c_dev: float = 10.0         # odchyłka wykonawcza Δc_dev [mm]
    c_nom_user: Optional[float] = None  # ręcznie przyjęta otulina nominalna (do strzemion)
    design_situation: str = "persistent"  # persistent | accidental


# ---------------------------------------------------------------------------
# Obciążenia
# ---------------------------------------------------------------------------
@dataclass
class LoadAction:
    name: str = "G"
    side: str = "R"
    category: str = "G"             # G, Q_A..Q_H, S, S_H, W, T, A
    nature: str = "characteristic"  # characteristic | design
    source: str = "beam_reaction"   # beam_reaction | support_reaction | point | other
    V: float = 0.0
    H: float = 0.0
    M: float = 0.0
    e_x: float = 0.0
    e_y: float = 0.0
    note: str = ""


@dataclass
class CombinationSettings:
    method: str = "6.10ab"          # 6.10 | 6.10ab
    gamma_G_sup: float = 1.35
    gamma_G_inf: float = 1.0
    gamma_Q: float = 1.5
    xi: float = 0.85
    include_sls: bool = True
    H_min_enabled: bool = False     # świadome założenie użytkownika
    H_min_ratio: float = 0.2
    H_min_source: str = ""


@dataclass
class LoadCombination:
    name: str = "KOMB"
    kind: str = "ULS"               # ULS | ULS_ACC | ULS_DIRECT | SLS_QP | SLS_CHAR
    factors: dict[str, float] = field(default_factory=dict)
    note: str = ""


@dataclass
class LoadsInput:
    actions: list[LoadAction] = field(default_factory=lambda: [
        LoadAction(name="G1", category="G", V=180e3, H=0.0, source="beam_reaction",
                   note="Reakcja od ciężaru własnego belki i stropu"),
        LoadAction(name="Q1", category="Q_B", V=120e3, H=0.0, source="beam_reaction",
                   note="Reakcja od obciążenia użytkowego"),
        LoadAction(name="H1", category="G", V=0.0, H=40e3, source="other",
                   note="Siła pozioma od ograniczenia odkształceń (skurcz/pełzanie) — wartość charakterystyczna"),
    ])
    combination_mode: str = "auto"  # auto | manual
    combinations: list[LoadCombination] = field(default_factory=list)
    settings: CombinationSettings = field(default_factory=CombinationSettings)


# ---------------------------------------------------------------------------
# Zbrojenie
# ---------------------------------------------------------------------------
@dataclass
class MainBarsInput:
    auto: bool = True
    phi: float = 20.0
    n_per_layer: int = 4
    layers: int = 1
    layer_gap: Optional[float] = None   # odstęp w świetle między warstwami (None = s_min)
    anchor_load: str = "loop"           # loop | bend_down | welded_bar | straight | mechanical
    anchor_column: str = "bend_down"    # bend_down | straight | continuous | mechanical
    mandrel_load: Optional[float] = None
    mandrel_column: Optional[float] = None
    column_leg: Optional[float] = None  # długość ramienia pionowego w słupie
    front_leg: Optional[float] = None   # długość ramienia pionowego na końcu wspornika
    welded_bar_phi: Optional[float] = None
    bond: str = "poor"                  # poor | good (warunki przyczepności, rys. 8.2)
    alpha3_mode: str = "conservative"   # conservative | computed
    K_alpha3: float = 0.05


@dataclass
class LinksInput:
    auto: bool = True
    h_phi: float = 10.0       # strzemiona poziome zamknięte
    h_count: int = 3
    h_zone: Optional[float] = None   # strefa rozmieszczenia poniżej cięgna (None = 2/3·d)
    v_phi: float = 8.0        # strzemiona pionowe zamknięte
    v_count: int = 0
    i_phi: float = 10.0       # pręty ukośne przy narożu wklęsłym (J.3(5))
    i_count: int = 0
    min_constructive_h: int = 2  # zalecenie konstrukcyjne (nie wymóg EC2)


@dataclass
class ReinforcementInput:
    main: MainBarsInput = field(default_factory=MainBarsInput)
    links: LinksInput = field(default_factory=LinksInput)
    allowed_diameters: list[float] = field(default_factory=lambda: [12.0, 14.0, 16.0, 20.0, 25.0, 28.0, 32.0])


# ---------------------------------------------------------------------------
# Model STM
# ---------------------------------------------------------------------------
@dataclass
class ManualNode:
    id: str = "N1"
    x: float = 0.0
    y: float = 0.0


@dataclass
class ManualMember:
    id: str = "M1"
    n1: str = "N1"
    n2: str = "N2"
    kind: str = "strut"        # strut | tie
    width: float = 100.0       # szerokość efektywna krzyżulca [mm]
    thickness: float = 400.0   # grubość (wymiar prostopadły) [mm]
    As: float = 0.0            # pole zbrojenia cięgna [mm²]


@dataclass
class ManualSupport:
    node: str = "N1"
    ux: bool = True
    uy: bool = True
    bearing_width: float = 100.0  # szerokość powierzchni docisku reakcji [mm]


@dataclass
class ManualLoad:
    node: str = "N1"
    Fx: float = 0.0     # wartość obliczeniowa [N]
    Fy: float = 0.0


@dataclass
class ManualStm:
    nodes: list[ManualNode] = field(default_factory=list)
    members: list[ManualMember] = field(default_factory=list)
    supports: list[ManualSupport] = field(default_factory=list)
    loads: list[ManualLoad] = field(default_factory=list)


@dataclass
class StmSettings:
    mode: str = "auto"                 # auto | manual
    lever_arm: str = "optimal"         # optimal | node_limit | user
    node_b_position: str = "in_column"  # in_column | face
    strut_limit: str = "6.56"          # 6.56 (strefa zarysowana) | 6.55
    node_10pct: bool = False           # zwiększenie σRd,max o 10% (6.5.4(5))
    node_10pct_justification: str = ""
    include_aH: bool = True            # uwzględnij ramię a_H siły H
    neglect_favourable_H: bool = True  # pomijaj korzystne działanie H skierowanej do słupa
    manual: ManualStm = field(default_factory=ManualStm)


# ---------------------------------------------------------------------------
# Parametry normowe
# ---------------------------------------------------------------------------
@dataclass
class NormativeInput:
    edition: str = "EC2-2004-PL"
    overrides: dict[str, float] = field(default_factory=dict)
    override_notes: dict[str, str] = field(default_factory=dict)
    ndp_confirmed: bool = False        # projektant potwierdził zgodność NDP z NA
    confirmed_params: list[str] = field(default_factory=list)  # potwierdzone parametry "do potwierdzenia"
    apply_engineering_recommendations: bool = True


# ---------------------------------------------------------------------------
# Projekt
# ---------------------------------------------------------------------------
@dataclass
class ProjectInfo:
    name: str = "Nowy projekt"
    number: str = ""
    object: str = ""
    element: str = "Wspornik krótki W-1"
    designer: str = ""
    checker: str = ""
    notes: str = ""


@dataclass
class Variant:
    name: str = "Wariant 1"
    geometry: GeometryInput = field(default_factory=GeometryInput)
    materials: MaterialsInput = field(default_factory=MaterialsInput)
    loads: LoadsInput = field(default_factory=LoadsInput)
    reinforcement: ReinforcementInput = field(default_factory=ReinforcementInput)
    stm: StmSettings = field(default_factory=StmSettings)
    normative: NormativeInput = field(default_factory=NormativeInput)


@dataclass
class Project:
    schema_version: int = SCHEMA_VERSION
    info: ProjectInfo = field(default_factory=ProjectInfo)
    variants: list[Variant] = field(default_factory=lambda: [Variant()])
    active: int = 0

    @property
    def current(self) -> Variant:
        if not self.variants:
            self.variants.append(Variant())
        self.active = max(0, min(self.active, len(self.variants) - 1))
        return self.variants[self.active]


def side_input(geo: GeometryInput, side: str) -> CorbelSideInput:
    """Zwraca dane strony wspornika (z uwzględnieniem odbicia lustrzanego)."""
    if side == "R":
        return geo.right
    if geo.left_mirror:
        import copy
        s = copy.deepcopy(geo.right)
        s.side = "L"
        return s
    return geo.left


def active_sides(geo: GeometryInput) -> list[str]:
    return ["R", "L"] if geo.layout == Layout.DOUBLE else ["R"]
