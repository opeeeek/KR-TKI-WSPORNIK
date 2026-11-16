"""Renderer prymitywów rysunkowych do grafiki wektorowej reportlab (raport PDF)."""
from __future__ import annotations

import math

from reportlab.graphics.shapes import Drawing, Line, PolyLine, Polygon, Circle, String, Rect
from reportlab.lib import colors
from reportlab.lib.units import mm

from ..palette import CANVAS
from ..visualization_engine import Scene, VIEW_LAYERS

FONT = "DejaVuSans"


def _col(key: str, alpha: float = 1.0):
    hexv = CANVAS["light"].get(key, CANVAS["light"]["line"])
    c = colors.HexColor(hexv)
    if alpha < 1.0:
        return colors.Color(c.red, c.green, c.blue, alpha=alpha)
    return c


def scene_to_drawing(scene: Scene, width: float = 170 * mm, max_height: float = 125 * mm,
                     layers: set[str] | None = None) -> Drawing:
    layers = set(layers or VIEW_LAYERS.get(scene.mode, VIEW_LAYERS["stm"]))
    layers.discard("handles")
    x0, y0, x1, y1 = scene.bounds
    sx = width / (x1 - x0)
    sy = max_height / (y1 - y0)
    s = min(sx, sy)
    W, H = (x1 - x0) * s, (y1 - y0) * s
    d = Drawing(W, H)
    d.add(Rect(0, 0, W, H, strokeColor=colors.HexColor("#bbbbbb"), fillColor=None, strokeWidth=0.4))

    def T(p):
        return ((p[0] - x0) * s, (p[1] - y0) * s)

    def flat(pts):
        out = []
        for p in pts:
            out += list(T(p))
        return out

    for pr in scene.prims:
        if pr.layer not in layers:
            continue
        sw = max(0.25, pr.width * 0.45)
        dash = [2.5, 1.8] if pr.dash else None
        if pr.kind in ("line", "polyline") and len(pr.pts) >= 2:
            d.add(PolyLine(flat(pr.pts), strokeColor=_col(pr.color, pr.alpha), strokeWidth=sw,
                           strokeDashArray=dash, strokeLineCap=1, strokeLineJoin=1))
        elif pr.kind == "polygon" and len(pr.pts) >= 3:
            d.add(Polygon(flat(pr.pts), strokeColor=_col(pr.color), strokeWidth=sw, strokeDashArray=dash,
                          fillColor=_col(pr.fill, pr.alpha if pr.alpha < 1 else 1.0) if pr.fill else None))
        elif pr.kind == "circle":
            cx, cy = T(pr.pts[0])
            d.add(Circle(cx, cy, max(pr.radius * s, 1.2), strokeColor=_col(pr.color), strokeWidth=sw,
                         fillColor=_col(pr.fill) if pr.fill else None))
        elif pr.kind == "arc":
            cx, cy = pr.pts[0]
            a0, da = pr.angles
            n = max(6, int(abs(da) / 5))
            pts = [(cx + pr.radius * math.cos(math.radians(a0 + da * i / n)),
                    cy + pr.radius * math.sin(math.radians(a0 + da * i / n))) for i in range(n + 1)]
            d.add(PolyLine(flat(pts), strokeColor=_col(pr.color), strokeWidth=sw))
        elif pr.kind == "arrow":
            (ax, ay), (bx, by) = T(pr.pts[0]), T(pr.pts[1])
            d.add(Line(ax, ay, bx, by, strokeColor=_col(pr.color), strokeWidth=sw))
            L = math.hypot(bx - ax, by - ay) or 1.0
            ux, uy = (bx - ax) / L, (by - ay) / L
            hl, hw = min(0.3 * L, 2.6 * mm), min(0.3 * L, 2.6 * mm) * 0.45
            d.add(Polygon([bx, by, bx - ux * hl - uy * hw, by - uy * hl + ux * hw,
                           bx - ux * hl + uy * hw, by - uy * hl - ux * hw], fillColor=_col(pr.color),
                          strokeColor=_col(pr.color), strokeWidth=0.2))
        elif pr.kind == "text" and pr.text:
            tx, ty = T(pr.pts[0])
            anchor = {"c": "middle", "l": "start", "r": "end"}.get(pr.anchor, "middle")
            d.add(String(tx, ty - 2, pr.text, fontName=FONT, fontSize=max(4.5, pr.size * 0.62),
                         fillColor=_col(pr.color or "text"), textAnchor=anchor))
        elif pr.kind == "dim":
            (xa, ya), (xb, yb) = pr.pts
            dx, dy = xb - xa, yb - ya
            L = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / L, dx / L
            o = pr.offset
            q1 = (xa + nx * o, ya + ny * o)
            q2 = (xb + nx * o, yb + ny * o)
            c = _col("dim")
            for pa, pb in (((xa, ya), q1), ((xb, yb), q2), (q1, q2)):
                (u1, v1), (u2, v2) = T(pa), T(pb)
                d.add(Line(u1, v1, u2, v2, strokeColor=c, strokeWidth=0.3))
            for q in (q1, q2):
                u, v = T(q)
                d.add(Line(u - 1.2, v - 1.2, u + 1.2, v + 1.2, strokeColor=c, strokeWidth=0.5))
            mx, my = T(((q1[0] + q2[0]) / 2, (q1[1] + q2[1]) / 2))
            ang = math.degrees(math.atan2(dy, dx))
            st = String(0, 1.2, pr.text, fontName=FONT, fontSize=5.2, fillColor=c, textAnchor="middle")
            if abs(abs(ang) - 90) < 1:
                from reportlab.graphics.shapes import Group
                g = Group(st)
                g.transform = (0, 1, -1, 0, mx - 1.5, my)
                d.add(g)
            else:
                st.x, st.y = mx, my + 1.2
                d.add(st)
    return d
