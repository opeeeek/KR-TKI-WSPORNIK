"""Silnik wizualizacji — niezależne od renderera prymitywy rysunkowe.

Ten sam zestaw prymitywów jest rysowany w GUI (Qt), w raporcie PDF
(reportlab) i w eksporcie DXF (ezdxf). Rysunek budowany jest WYŁĄCZNIE z
obiektów wynikowych analizy (``AnalysisResult``): geometria z
``GeometryModel``, węzły z kratownicy rozwiązanej przez solver. Funkcja
:func:`verify_scene` sprawdza zgodność rysunku z modelem obliczeniowym.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .core.model import Variant
from .geometry_engine import GeometryModel, build_geometry

Point = tuple[float, float]

LAYERS = {
    "column": "Słup",
    "outline": "Kontur wspornika",
    "axes": "Osie",
    "cover": "Otulina",
    "plate": "Płyta oporowa",
    "loads": "Obciążenia",
    "dims": "Wymiary",
    "rebar_main": "Zbrojenie główne",
    "links": "Strzemiona",
    "marks": "Oznaczenia prętów",
    "stm_struts": "Krzyżulce (STM)",
    "stm_ties": "Cięgna (STM)",
    "stm_nodes": "Węzły (STM)",
    "stm_zones": "Strefy węzłowe i szerokości",
    "forces": "Wartości sił",
    "angles": "Kąty",
    "reactions": "Reakcje",
    "stress": "Wykorzystanie / koncentracje",
    "handles": "Uchwyty edycji",
}

VIEW_LAYERS = {
    "geometry": {"column", "outline", "axes", "plate", "loads", "dims", "handles"},
    "stm": {"column", "outline", "plate", "loads", "stm_struts", "stm_ties", "stm_nodes", "stm_zones", "forces",
            "angles", "reactions", "handles"},
    "stress": {"column", "outline", "plate", "stm_struts", "stm_ties", "stm_nodes", "stm_zones", "stress", "forces"},
    "rebar": {"column", "outline", "cover", "plate", "rebar_main", "links", "marks", "dims"},
}
VIEW_NAMES = {"geometry": "Geometria", "stm": "Model STM", "stress": "Naprężenia / wykorzystanie",
              "rebar": "Zbrojenie"}


@dataclass
class Prim:
    kind: str                       # line | polyline | polygon | circle | text | arrow | dim | arc | handle
    layer: str
    pts: list[Point] = field(default_factory=list)
    color: str = "line"             # klucz koloru semantycznego
    width: float = 1.0              # grubość [px ekranowe]
    dash: bool = False
    fill: str | None = None
    alpha: float = 1.0
    text: str = ""
    size: float = 9.0               # wysokość tekstu [pt ekranowe]
    ref: str = ""
    radius: float = 0.0
    eta: float | None = None
    angles: tuple[float, float] = (0.0, 0.0)   # łuk: kąt początkowy i rozwartość [deg]
    offset: float = 0.0             # wymiar: odsunięcie linii wymiarowej [mm]
    anchor: str = "c"               # text: c | l | r


@dataclass
class Scene:
    prims: list[Prim]
    bounds: tuple[float, float, float, float]
    mode: str
    combination: str
    geometry_signature: tuple
    node_coords: dict[str, Point]
    stale: bool = False
    title: str = ""

    def layer_prims(self, visible: set[str]) -> list[Prim]:
        return [p for p in self.prims if p.layer in visible]


def _bounds(pts: list[Point], margin: float = 0.12) -> tuple[float, float, float, float]:
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    dx, dy = (x1 - x0) or 1.0, (y1 - y0) or 1.0
    return x0 - margin * dx, y0 - margin * dy, x1 + margin * dx, y1 + margin * dy


def _fmt_kN(v: float) -> str:
    return f"{v / 1e3:.1f} kN".replace(".", ",")


def eta_color(eta: float | None) -> str:
    if eta is None:
        return "line"
    if eta > 1.0 + 1e-9:
        return "eta_fail"
    if eta > 0.85:
        return "eta_high"
    if eta > 0.5:
        return "eta_mid"
    return "eta_low"


def build_scene(variant: Variant, result=None, mode: str = "stm", combination: str | None = None,
                stale: bool = False) -> Scene:
    """Buduje scenę. Gdy ``result`` jest None lub nieaktualny, rysowana jest tylko geometria z danych
    wejściowych (bez modelu STM i zbrojenia z obliczeń) — nie dopuszcza to do sytuacji, w której
    rysunek pokazuje model inny niż dane bieżące."""
    use_result = result is not None and not stale and result.geometry is not None
    gm: GeometryModel = result.geometry if use_result else build_geometry(variant.geometry)
    prims: list[Prim] = []
    _geometry(prims, gm)
    node_coords: dict[str, Point] = {}
    combo = ""
    if use_result:
        combo = combination if combination in result.stm else result.governing
        sr = result.stm.get(combo)
        if sr is not None:
            node_coords = {n.id: (n.x, n.y) for n in sr.truss.nodes}
            _loads(prims, gm, sr)
            _stm(prims, gm, sr, result)
        if result.main is not None and result.cover is not None:
            _rebar(prims, gm, result)
    else:
        _loads_input(prims, gm, variant)
    _dims(prims, gm)
    _handles(prims, gm, variant, result if use_result else None, combo)
    pts = [q for p in prims if p.layer in ("column", "outline", "dims", "rebar_main") for q in p.pts]
    return Scene(prims, _bounds(pts), mode, combo, gm.signature(), node_coords, stale=stale or result is None,
                 title=VIEW_NAMES.get(mode, mode))


# ---------------------------------------------------------------------------
def column_extent(gm: GeometryModel) -> tuple[float, float]:
    """Zakres rysowanego fragmentu słupa (rysunek z liniami urwania; obliczenia używają pełnej geometrii)."""
    top = min(gm.above, max(250.0, 0.5 * gm.h_max))
    bot = -(gm.h_max + min(gm.below, max(300.0, 0.6 * gm.h_max)))
    return top, bot


def _break_line(x0: float, x1: float, y: float, amp: float) -> list[Point]:
    xm = (x0 + x1) / 2.0
    w = (x1 - x0)
    return [(x0 - 20, y), (xm - 0.06 * w, y), (xm - 0.02 * w, y + amp), (xm + 0.02 * w, y - amp),
            (xm + 0.06 * w, y), (x1 + 20, y)]


def _geometry(prims: list[Prim], gm: GeometryModel) -> None:
    h2 = gm.h_col / 2.0
    top, bot = column_extent(gm)
    prims.append(Prim("polygon", "column", [(-h2, top), (h2, top), (h2, bot), (-h2, bot)], color="concrete_edge",
                      width=1.2, fill="column_fill", ref="geom:column"))
    amp = 0.06 * gm.h_col
    if gm.above > top + 1e-6:
        prims.append(Prim("polyline", "column", _break_line(-h2, h2, top, amp), color="concrete_edge", width=1.0))
    if -(gm.h_max + gm.below) < bot - 1e-6:
        prims.append(Prim("polyline", "column", _break_line(-h2, h2, bot, amp), color="concrete_edge", width=1.0))
    for sd, sg in gm.sides.items():
        prims.append(Prim("polygon", "outline", sg.outline(), color="concrete_edge", width=1.6, fill="concrete_fill",
                          ref=f"geom:corbel:{sd}"))
        # płyta oporowa
        p = sg.plate
        x0, _ = sg.g(p.xi_inner, 0)
        x1, _ = sg.g(p.xi_outer, 0)
        x0, x1 = min(x0, x1), max(x0, x1)
        t = max(p.thickness, 6.0) if p.kind != "direct" else 4.0
        prims.append(Prim("polygon", "plate", [(x0, 0), (x1, 0), (x1, t), (x0, t)], color="plate_edge", width=1.0,
                          fill="plate_fill", ref=f"geom:plate:{sd}"))
    prims.append(Prim("line", "axes", [(0.0, top + 30), (0.0, bot - 30)], color="axis", width=0.8, dash=True))
    prims.append(Prim("text", "axes", [(0.0, top + 50)], text="oś słupa", color="axis", size=8))
    xr = h2 + max(s.l_c for s in gm.sides.values()) + 60
    xl = -xr if "L" in gm.sides else -h2 - 60
    prims.append(Prim("line", "axes", [(xl, 0.0), (xr, 0.0)], color="axis", width=0.5, dash=True))


def _arrow(prims, layer, tip: Point, vec: Point, color: str, text: str, ref: str = "", width: float = 2.0):
    tail = (tip[0] - vec[0], tip[1] - vec[1])
    prims.append(Prim("arrow", layer, [tail, tip], color=color, width=width, ref=ref))
    if text:
        mid = ((tail[0] + tip[0]) / 2, (tail[1] + tip[1]) / 2)
        if abs(vec[0]) < 1e-9:      # strzałka pionowa — opis z boku
            prims.append(Prim("text", layer, [(mid[0] + 18, mid[1])], text=text, color=color, size=9, ref=ref,
                              anchor="l"))
        else:                       # strzałka pozioma — opis nad strzałką
            prims.append(Prim("text", layer, [(mid[0], mid[1] + 26)], text=text, color=color, size=9, ref=ref,
                              anchor="c"))


def _loads(prims, gm, sr) -> None:
    for sd, sm in sr.sides.items():
        sg = gm.sides[sd]
        p = sm.params
        x_load = sg.g(sg.a_c + (p.M / p.V if p.V else 0.0), 0)[0]
        top = sg.plate.thickness if sg.plate.kind != "direct" else 4.0
        L = max(120.0, 0.35 * sg.h_c)
        _arrow(prims, "loads", (x_load, top), (0.0, -L), "load", f"V_Ed = {_fmt_kN(p.V)}", f"load:V{sd}", 2.4)
        if abs(p.H_raw) > 1e-6:
            dirx = sg.s * (1 if p.H_raw > 0 else -1)
            tail = (x_load, top + 12)
            tip = (x_load + dirx * L * 0.8, top + 12)
            prims.append(Prim("arrow", "loads", [tail, tip], color="load", width=2.0, ref=f"load:H{sd}"))
            prims.append(Prim("text", "loads", [(tip[0], tip[1] + 28)], text=f"H_Ed = {_fmt_kN(p.H_raw)}",
                              color="load", size=9, ref=f"load:H{sd}", anchor="l" if dirx > 0 else "r"))


def _loads_input(prims, gm, variant) -> None:
    for sd, sg in gm.sides.items():
        x = sg.g(sg.a_c, 0)[0]
        L = max(120.0, 0.35 * sg.h_c)
        top = sg.plate.thickness if sg.plate.kind != "direct" else 4.0
        _arrow(prims, "loads", (x, top), (0.0, -L), "load", "V", f"load:V{sd}", 2.4)


def _stm(prims, gm, sr, result) -> None:
    eta_by_ref: dict[str, float] = {}
    for c in result.checks:
        if c.element_ref and c.eta is not None and math.isfinite(c.eta) and c.combination in ("", sr.combination,
                                                                                               "obwiednia SGN"):
            eta_by_ref[c.element_ref] = max(eta_by_ref.get(c.element_ref, 0.0), c.eta)
    crit = result.critical()
    crit_ref = crit.element_ref if crit else ""
    # krzyżulce
    for s in sr.struts:
        ref = f"member:{s.id}"
        eta = eta_by_ref.get(ref)
        prims.append(Prim("polygon", "stm_zones", s.polygon, color="strut", width=0.8, dash=True, fill="strut_fill",
                          alpha=0.25, ref=ref))
        prims.append(Prim("polygon", "stress", s.polygon, color=eta_color(eta), width=0.8, fill=eta_color(eta),
                          alpha=0.45, ref=ref, eta=eta))
        a = sr.truss.node(s.n1)
        b = sr.truss.node(s.n2)
        prims.append(Prim("line", "stm_struts", [(a.x, a.y), (b.x, b.y)], color="strut", width=3.2, dash=True,
                          ref=ref))
        mx, my = (a.x + b.x) / 2, (a.y + b.y) / 2
        prims.append(Prim("text", "forces", [(mx, my)], text=f"{s.id}: C = {_fmt_kN(abs(s.force))}", color="strut",
                          size=9, ref=ref))
        # szerokości efektywne
        Ls = math.hypot(b.x - a.x, b.y - a.y) or 1.0
        nx, ny = (b.y - a.y) / Ls, -(b.x - a.x) / Ls
        if nx < 0:
            nx, ny = -nx, -ny
        for (px, py), w in (((a.x + (b.x - a.x) * 0.18, a.y + (b.y - a.y) * 0.18), s.w1),
                            ((a.x + (b.x - a.x) * 0.82, a.y + (b.y - a.y) * 0.82), s.w2)):
            prims.append(Prim("text", "stm_zones", [(px + nx * (w / 2 + 25), py + ny * (w / 2 + 25))],
                              text=f"w = {w:.0f}", color="strut", size=7, ref=ref, anchor="l"))
        # kąt nachylenia przy węźle B
        ang0 = 0.0 if b.x < a.x else 180.0 - s.theta_deg
        R = 0.35 * s.length
        prims.append(Prim("arc", "angles", [(b.x, b.y)], color="angle", width=1.0, radius=R,
                          angles=(ang0, s.theta_deg), ref=ref))
        tx = b.x + R * 1.08 * math.cos(math.radians(ang0 + s.theta_deg / 2))
        ty = b.y + R * 1.08 * math.sin(math.radians(ang0 + s.theta_deg / 2))
        prims.append(Prim("text", "angles", [(tx, ty)], text=f"θ = {s.theta_deg:.1f}°".replace(".", ","),
                          color="angle", size=8, ref=ref))
        if s.shape == "butelkowy":
            prims.append(Prim("text", "stm_zones", [(mx, my - 0.08 * s.length)], text="krzyżulec butelkowy",
                              color="strut", size=7, ref=ref))
    # cięgna
    for t in sr.ties:
        ref = f"member:{t.id}"
        eta = eta_by_ref.get(ref)
        a = sr.truss.node(t.n1)
        b = sr.truss.node(t.n2)
        prims.append(Prim("polygon", "stm_zones", t.polygon, color="tie", width=0.6, dash=True, fill="tie_fill",
                          alpha=0.15, ref=ref))
        prims.append(Prim("line", "stm_ties", [(a.x, a.y), (b.x, b.y)], color="tie", width=3.2, ref=ref))
        prims.append(Prim("line", "stress", [(a.x, a.y), (b.x, b.y)], color=eta_color(eta), width=5.0, ref=ref,
                          eta=eta))
        mx = (a.x + b.x) / 2
        prims.append(Prim("text", "forces", [(mx, a.y + t.u / 2 + 30)], text=f"{t.id}: T = {_fmt_kN(t.force)}",
                          color="tie", size=9, ref=ref))
    # strefy węzłowe i węzły
    for nid, nz in sr.nodes.items():
        ref = f"node:{nid}"
        eta = eta_by_ref.get(ref)
        if nz.polygon:
            prims.append(Prim("polygon", "stm_zones", nz.polygon, color="node", width=1.0, dash=True, ref=ref))
            prims.append(Prim("polygon", "stress", nz.polygon, color=eta_color(eta), width=1.0, fill=eta_color(eta),
                              alpha=0.5, ref=ref, eta=eta))
        prims.append(Prim("circle", "stm_nodes", [nz.center], color="node", width=1.5, fill="node_fill", radius=11.0,
                          ref=ref))
        prims.append(Prim("text", "stm_nodes", [(nz.center[0] + 14, nz.center[1] + 14)],
                          text=f"{nid} ({nz.type})" if nz.type in ("CCC", "CCT", "CTT") else nid, color="node",
                          size=8, ref=ref, anchor="l"))
        if eta is not None:
            prims.append(Prim("text", "stress", [(nz.center[0] + 14, nz.center[1] - 14)],
                              text=f"η = {eta:.2f}".replace(".", ","), color=eta_color(eta), size=8, ref=ref,
                              anchor="l"))
    for s in sr.struts:
        eta = eta_by_ref.get(f"member:{s.id}")
        if eta is not None:
            a = sr.truss.node(s.n1)
            b = sr.truss.node(s.n2)
            prims.append(Prim("text", "stress", [((a.x + b.x) / 2, (a.y + b.y) / 2 - 40)],
                              text=f"η = {eta:.2f}".replace(".", ","), color=eta_color(eta), size=9,
                              ref=f"member:{s.id}"))
    # reakcje (siły od słupa)
    for nid, (rx, ry) in sr.solution.reactions.items():
        n = sr.truss.node(nid)
        Lr = 110.0
        if abs(rx) > 1.0:
            _arrow(prims, "reactions", (n.x, n.y - (35.0 if nid == "C" else 0.0)), (math.copysign(Lr, rx), 0.0),
                   "reaction", f"R_x = {_fmt_kN(abs(rx))}", f"node:{nid}", 1.6)
        if abs(ry) > 1.0:
            _arrow(prims, "reactions", (n.x, n.y), (0.0, math.copysign(Lr, ry)), "reaction",
                   f"R_y = {_fmt_kN(abs(ry))}", f"node:{nid}", 1.6)
    # element krytyczny
    if crit_ref:
        for nid, nz in sr.nodes.items():
            if crit_ref == f"node:{nid}":
                prims.append(Prim("circle", "stress", [nz.center], color="critical", width=3.0, radius=26.0,
                                  ref=crit_ref, text="krytyczny"))
        for s in sr.struts + sr.ties:
            if crit_ref == f"member:{s.id}":
                a = sr.truss.node(s.n1)
                b = sr.truss.node(s.n2)
                prims.append(Prim("line", "stress", [(a.x, a.y), (b.x, b.y)], color="critical", width=9.0, alpha=0.45,
                                  ref=crit_ref, text="krytyczny"))


def _rebar(prims, gm, result) -> None:
    ml, cv, mb = result.main, result.cover, result.main_input
    h2 = gm.h_col / 2.0
    double = len(gm.sides) == 2
    col_in = gm.column_cover + gm.column_phi_link + gm.column_phi_long
    mand = result.mandrels
    # słup: pręty podłużne
    for x in (-h2 + gm.column_cover + gm.column_phi_link + gm.column_phi_long / 2,
              h2 - gm.column_cover - gm.column_phi_link - gm.column_phi_long / 2):
        ctop, cbot = column_extent(gm)
        prims.append(Prim("line", "rebar_main", [(x, ctop), (x, cbot)], color="rebar_col",
                          width=1.2, dash=True, ref="rebar:column"))
    # otulina (linia przerywana)
    for sd, sg in gm.sides.items():
        c = cv.c_nom
        loc = [(0.0, -c), (sg.l_c - c, -c), (sg.l_c - c, -sg.h_e + c)]
        if sg.x_slope > 0:
            loc.append((sg.x_slope, -sg.h_c + c))
        loc.append((0.0, -sg.h_c + c))
        prims.append(Prim("polyline", "cover", [sg.g(*q) for q in loc], color="cover", width=0.8, dash=True,
                          ref="rebar:cover"))
    # zbrojenie główne
    for k, depth in enumerate(ml.layer_depths):
        y = -depth
        if double:
            xL = gm.sides["L"].g(gm.sides["L"].l_c - cv.c_nom - ml.phi / 2, 0)[0]
            xR = gm.sides["R"].g(gm.sides["R"].l_c - cv.c_nom - ml.phi / 2, 0)[0]
            pts = [(xL, y), (xR, y)]
            if mb.anchor_load == "bend_down":
                legL = mand.get("leg_front", 5 * ml.phi)
                pts = [(xL, y - legL)] + pts + [(xR, y - legL)]
        else:
            sg = gm.sides["R"]
            x_end = sg.g(sg.l_c - cv.c_nom - ml.phi / 2, 0)[0]
            x_col = -h2 + col_in + ml.phi / 2
            pts = [(x_col, y), (x_end, y)]
            if mb.anchor_column == "bend_down":
                pts = [(x_col, y - mand.get("leg_col", 5 * ml.phi))] + pts
            if mb.anchor_load == "bend_down":
                pts = pts + [(x_end, y - mand.get("leg_front", 5 * ml.phi))]
        prims.append(Prim("polyline", "rebar_main", pts, color="rebar", width=3.0, ref="rebar:main",
                          text=f"{ml.n}φ{ml.phi:.0f}"))
        for sd, sg in gm.sides.items():
            if mb.anchor_load == "welded_bar":
                xw = sg.g(sg.l_c - cv.c_nom - ml.phi, 0)[0]
                prims.append(Prim("circle", "rebar_main", [(xw, y - ml.phi)], color="rebar", width=1.5, fill="rebar",
                                  radius=ml.phi / 2, ref="rebar:main"))
            if mb.anchor_load == "loop":
                xw = sg.g(sg.l_c - cv.c_nom - ml.phi / 2, 0)[0]
                prims.append(Prim("text", "marks", [(xw, y + 25)], text="pętla", color="rebar", size=7,
                                  ref="rebar:main"))
    prims.append(Prim("text", "marks", [(0.0, -ml.layer_depths[0] + 28)],
                      text=f"(1) {ml.desc()}", color="rebar", size=9, ref="rebar:main"))
    # strzemiona
    mark = 2 + (1 if mb.anchor_load == "welded_bar" else 0)
    for sd, ll in result.links.items():
        sg = gm.sides[sd]
        for dpt in ll.h_depths:
            xi_max = sg.l_c - cv.c_nom
            target = dpt + cv.c_nom
            if sg.h_e < sg.h_c and target > sg.h_e and sg.l_c > sg.x_slope:
                t = (sg.h_c - target) / (sg.h_c - sg.h_e)
                xi_max = min(xi_max, sg.x_slope + t * (sg.l_c - sg.x_slope))
            x0 = -sg.s * (h2 - col_in) if not double else -sg.s * 0.0
            x1 = sg.g(xi_max, 0)[0]
            prims.append(Prim("line", "links", [(x0, -dpt), (x1, -dpt)], color="link", width=1.6, ref="rebar:links"))
        if ll.h_depths:
            xm = sg.g(sg.l_c * 0.55, 0)[0]
            prims.append(Prim("text", "marks", [(xm, -ll.h_depths[-1] - 22)],
                              text=f"({mark}) {len(ll.h_depths)}×φ{ll.h_phi:.0f} poz.", color="link", size=8,
                              ref="rebar:links"))
            mark += 1
        for xi in ll.v_positions:
            h = sg.depth_at(xi)
            x = sg.g(xi, 0)[0]
            prims.append(Prim("line", "links", [(x, -cv.c_nom), (x, -h + cv.c_nom)], color="link", width=1.6,
                              ref="rebar:links"))
        if ll.v_positions:
            prims.append(Prim("text", "marks", [(sg.g(ll.v_positions[0], 0)[0], -sg.h_c - 30)],
                              text=f"({mark}) {len(ll.v_positions)}×φ{ll.v_phi:.0f} pion.", color="link", size=8,
                              ref="rebar:links"))
            mark += 1
        for k in range(ll.i_count):
            off = 40.0 + 45.0 * k
            p0 = sg.g(-off * 1.2, -sg.h_c - 120 + off)
            p1 = sg.g(off + 160, -sg.h_c + off + 160 - 120 + 120)
            prims.append(Prim("line", "links", [p0, p1], color="link", width=1.4, ref="rebar:links"))


def _dim(prims, p1: Point, p2: Point, offset: float, text: str) -> None:
    prims.append(Prim("dim", "dims", [p1, p2], color="dim", width=0.8, text=text, offset=offset, size=8))


def _dims(prims, gm: GeometryModel) -> None:
    """Wymiary. Konwencja: odsunięcie linii wymiarowej wzdłuż normalnej n = (−dy, dx)/L odcinka p1→p2."""
    h2 = gm.h_col / 2.0
    _dim(prims, (-h2, gm.above), (h2, gm.above), 60.0, f"h_col = {gm.h_col:.0f}")
    for sd, sg in gm.sides.items():
        s = sg.s
        face = sg.x_face
        end = sg.g(sg.l_c, 0)[0]
        off = 80.0 + 0.1 * sg.h_c
        _dim(prims, (face, 0.0), (end, 0.0), s * (off + 60), f"l_c = {sg.l_c:.0f}")
        xa = sg.g(sg.a_c, 0)[0]
        _dim(prims, (face, 0.0), (xa, 0.0), s * off, f"a_c = {sg.a_c:.0f}")
        _dim(prims, (end, 0.0), (end, -sg.h_e), s * 70.0, f"h_e = {sg.h_e:.0f}")
        _dim(prims, (face, 0.0), (face, -sg.h_c), s * 45.0, f"h_c = {sg.h_c:.0f}")
        pl = sg.plate
        x0 = sg.g(pl.xi_inner, 0)[0]
        x1 = sg.g(pl.xi_outer, 0)[0]
        _dim(prims, (min(x0, x1), pl.thickness), (max(x0, x1), pl.thickness), 30.0, f"a_p = {pl.length:.0f}")


def _handles(prims, gm, variant, result, combo) -> None:
    for sd, sg in gm.sides.items():
        prims.append(Prim("handle", "handles", [sg.g(sg.a_c, 0)], color="handle", radius=7, ref=f"handle:a_c:{sd}",
                          text="a_c"))
        prims.append(Prim("handle", "handles", [sg.g(sg.l_c, -sg.h_e / 2)], color="handle", radius=7,
                          ref=f"handle:l_c:{sd}", text="l_c"))
        prims.append(Prim("handle", "handles", [sg.g(sg.l_c, -sg.h_e)], color="handle", radius=7,
                          ref=f"handle:h_e:{sd}", text="h_e"))
        prims.append(Prim("handle", "handles", [sg.g(0.0, -sg.h_c)], color="handle", radius=7,
                          ref=f"handle:h_c:{sd}", text="h_c"))
        if result is not None and combo in result.stm:
            sm = result.stm[combo].sides.get(sd)
            if sm is not None:
                prims.append(Prim("handle", "handles", [sg.g(sm.state.xi_B, sm.state.y_B)], color="handle_stm",
                                  radius=7, ref=f"handle:x_c:{sd}", text="x_c"))
    if variant.stm.mode == "manual":
        for nd in variant.stm.manual.nodes:
            prims.append(Prim("handle", "handles", [(nd.x, nd.y)], color="handle_stm", radius=7,
                              ref=f"handle:node:{nd.id}", text=nd.id))


def verify_scene(scene: Scene, result) -> list[str]:
    """Kontrola zgodności rysunku z modelem obliczeniowym. Zwraca listę niezgodności (pusta = zgodny)."""
    issues: list[str] = []
    if result is None or scene.stale:
        if any(p.layer.startswith("stm_") for p in scene.prims):
            issues.append("Scena nieaktualna zawiera elementy modelu STM.")
        return issues
    if result.geometry is None:
        return issues
    if scene.geometry_signature != result.geometry.signature():
        issues.append("Geometria rysunku różni się od geometrii użytej w obliczeniach.")
    sr = result.stm.get(scene.combination)
    if sr is not None:
        for n in sr.truss.nodes:
            p = scene.node_coords.get(n.id)
            if p is None or abs(p[0] - n.x) > 1e-9 or abs(p[1] - n.y) > 1e-9:
                issues.append(f"Węzeł {n.id}: położenie na rysunku niezgodne z modelem.")
        drawn = {p.ref for p in scene.prims if p.layer in ("stm_struts", "stm_ties")}
        for m in sr.truss.members:
            if f"member:{m.id}" not in drawn:
                issues.append(f"Pręt {m.id} nie został narysowany.")
    return issues
