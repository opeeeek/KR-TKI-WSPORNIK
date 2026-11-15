"""Silnik geometrii wspornika i słupa.

Globalny układ współrzędnych (rysunek i model STM):
* początek w osi słupa na poziomie górnej powierzchni wspornika;
* oś x pozioma (w prawo), oś y pionowa (w górę);
* wspornik prawy (R) od x = +h_col/2, lewy (L) od x = −h_col/2.

Lokalny układ strony wspornika: ξ — odległość od lica słupa w kierunku
wysięgu (≥ 0 we wsporniku, < 0 wewnątrz słupa), y — jak globalnie.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .core.model import GeometryInput, Layout, side_input, active_sides

Point = tuple[float, float]


@dataclass
class PlateGeom:
    kind: str
    length: float
    width: float
    thickness: float
    xi_center: float     # położenie środka płyty od lica (lokalnie)

    @property
    def xi_inner(self) -> float:
        return self.xi_center - self.length / 2.0

    @property
    def xi_outer(self) -> float:
        return self.xi_center + self.length / 2.0


@dataclass
class SideGeom:
    side: str
    s: int               # +1 prawy, −1 lewy
    l_c: float
    h_c: float
    h_e: float
    x_slope: float
    a_c: float
    plate: PlateGeom
    x_face: float        # globalne x lica słupa

    def depth_at(self, xi: float) -> float:
        """Wysokość wspornika w odległości ξ od lica."""
        if xi <= self.x_slope or self.l_c <= self.x_slope:
            return self.h_c
        if xi >= self.l_c:
            return self.h_e
        t = (xi - self.x_slope) / (self.l_c - self.x_slope)
        return self.h_c + t * (self.h_e - self.h_c)

    def g(self, xi: float, y: float) -> Point:
        """Przeliczenie współrzędnych lokalnych (ξ, y) na globalne (x, y)."""
        return (self.x_face + self.s * xi, y)

    def local_outline(self) -> list[Point]:
        pts = [(0.0, 0.0), (self.l_c, 0.0), (self.l_c, -self.h_e)]
        if self.x_slope > 1e-9 and self.x_slope < self.l_c - 1e-9:
            pts.append((self.x_slope, -self.h_c))
        pts.append((0.0, -self.h_c))
        return pts

    def outline(self) -> list[Point]:
        return [self.g(xi, y) for xi, y in self.local_outline()]

    @property
    def shape(self) -> str:
        if abs(self.h_e - self.h_c) < 1e-9:
            return "stała wysokość"
        if self.x_slope > 1e-9:
            return "zmienna wysokość (skos od ξ = %.0f mm)" % self.x_slope
        return "ukośna dolna krawędź (zmienna wysokość)"

    @property
    def volume_per_b(self) -> float:
        """Pole przekroju podłużnego wspornika [mm²]."""
        a1 = self.h_c * min(self.x_slope, self.l_c)
        rest = max(self.l_c - self.x_slope, 0.0)
        return a1 + rest * (self.h_c + self.h_e) / 2.0


@dataclass
class GeometryModel:
    layout: Layout
    construction: str
    b: float
    h_col: float
    b_col: float
    above: float
    below: float
    column_cover: float
    column_phi_long: float
    column_phi_link: float
    sides: dict[str, SideGeom] = field(default_factory=dict)

    @property
    def h_max(self) -> float:
        return max(s.h_c for s in self.sides.values())

    def column_rect(self) -> list[Point]:
        h2 = self.h_col / 2.0
        top, bot = self.above, -(self.h_max + self.below)
        return [(-h2, top), (h2, top), (h2, bot), (-h2, bot)]

    def outline(self) -> list[Point]:
        """Obrys całości (słup + wsporniki) jako jeden wielokąt prosty (CCW nieistotne)."""
        h2 = self.h_col / 2.0
        top, bot = self.above, -(self.h_max + self.below)
        pts: list[Point] = [(-h2, top), (h2, top)]
        if "R" in self.sides:
            r = self.sides["R"]
            pts += [(h2, 0.0)] + [r.g(xi, y) for xi, y in r.local_outline()[1:-1]] + [(h2, -r.h_c)]
        pts += [(h2, bot), (-h2, bot)]
        if "L" in self.sides:
            lft = self.sides["L"]
            loc = lft.local_outline()
            # obieg w przeciwną stronę: od dołu lica do góry
            pts += [(-h2, -lft.h_c)] + [lft.g(xi, y) for xi, y in reversed(loc[1:-1])] + [(-h2, 0.0)]
        return pts

    def contains(self, p: Point, tol: float = 1e-6) -> bool:
        return point_in_polygon(p, self.outline(), tol)

    def ray_distance(self, p: Point, d: Point) -> float:
        """Odległość od punktu p w kierunku d do brzegu obrysu."""
        return ray_polygon_distance(p, d, self.outline())

    def concrete_area_side(self, side: str) -> float:
        return self.sides[side].volume_per_b

    def signature(self) -> tuple:
        """Sygnatura geometrii (do kontroli zgodności rysunku z obliczeniami)."""
        sig = [round(self.b, 6), round(self.h_col, 6), round(self.b_col, 6)]
        for k in sorted(self.sides):
            s = self.sides[k]
            sig += [k, round(s.l_c, 6), round(s.h_c, 6), round(s.h_e, 6), round(s.x_slope, 6),
                    round(s.a_c, 6), round(s.plate.xi_center, 6), round(s.plate.length, 6)]
        return tuple(sig)


def build_geometry(geo: GeometryInput) -> GeometryModel:
    gm = GeometryModel(
        layout=geo.layout, construction=geo.construction.value if hasattr(geo.construction, "value")
        else str(geo.construction), b=geo.b, h_col=geo.column.h_col, b_col=geo.column.b_col,
        above=geo.column.above, below=geo.column.below, column_cover=geo.column.cover,
        column_phi_long=geo.column.phi_long, column_phi_link=geo.column.phi_link)
    for sd in active_sides(geo):
        si = side_input(geo, sd)
        s = 1 if sd == "R" else -1
        plate = PlateGeom(si.plate.kind, si.plate.length, si.plate.width, si.plate.thickness,
                          si.a_c + si.plate.offset)
        gm.sides[sd] = SideGeom(sd, s, si.l_c, si.h_c, si.h_e, min(max(si.x_slope, 0.0), si.l_c), si.a_c,
                                plate, s * geo.column.h_col / 2.0)
    return gm


# ---------------------------------------------------------------------------
# Geometria obliczeniowa
# ---------------------------------------------------------------------------
def point_in_polygon(p: Point, poly: list[Point], tol: float = 1e-6) -> bool:
    x, y = p
    # punkt na brzegu → traktowany jako wewnątrz
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        if _dist_point_segment(p, a, b) <= tol:
            return True
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y):
            xint = xi + (y - yi) * (xj - xi) / (yj - yi)
            if x < xint:
                inside = not inside
        j = i
    return inside


def _dist_point_segment(p: Point, a: Point, b: Point) -> float:
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def ray_polygon_distance(p: Point, d: Point, poly: list[Point]) -> float:
    dx, dy = d
    L = math.hypot(dx, dy)
    dx, dy = dx / L, dy / L
    best = math.inf
    n = len(poly)
    for i in range(n):
        (ax, ay), (bx, by) = poly[i], poly[(i + 1) % n]
        ex, ey = bx - ax, by - ay
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        t = ((ax - p[0]) * ey - (ay - p[1]) * ex) / den
        u = ((ax - p[0]) * dy - (ay - p[1]) * dx) / den
        if t > 1e-9 and -1e-9 <= u <= 1 + 1e-9:
            best = min(best, t)
    return best


def segment_inside(a: Point, b: Point, poly: list[Point], samples: int = 41, tol: float = 0.5) -> bool:
    for i in range(samples):
        t = i / (samples - 1)
        if not point_in_polygon((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])), poly, tol):
            return False
    return True


def polygon_area(poly: list[Point]) -> float:
    a = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0
