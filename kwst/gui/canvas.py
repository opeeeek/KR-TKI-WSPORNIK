"""Interaktywny widok rysunku (QGraphicsView): zoom, przesuwanie, warstwy, wybór elementu,
uchwyty edycji geometrii / węzłów, pomiar odległości, podświetlanie elementu krytycznego."""
from __future__ import annotations

import math

from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import (QBrush, QColor, QPainter, QPainterPath, QPen, QPolygonF, QFont, QTransform)
from PySide6.QtWidgets import (QGraphicsEllipseItem, QGraphicsItem, QGraphicsPathItem, QGraphicsScene,
                               QGraphicsSimpleTextItem, QGraphicsView, QLabel, QGraphicsRectItem)

from ..visualization_engine import Scene, Prim, VIEW_LAYERS
from .themes import canvas_color


def _p(pt) -> QPointF:
    return QPointF(pt[0], -pt[1])     # oś y rysunku do góry


class HandleItem(QGraphicsEllipseItem):
    def __init__(self, view: "DrawingView", prim: Prim, color: QColor):
        r = prim.radius or 7.0
        super().__init__(-r, -r, 2 * r, 2 * r)
        self.view = view
        self.ref = prim.ref
        self.setPos(_p(prim.pts[0]))
        self.setBrush(QBrush(color))
        self.setPen(QPen(QColor("#000000"), 1))
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setZValue(100)
        self.setCursor(Qt.SizeAllCursor)
        self.setToolTip(f"Przeciągnij, aby zmienić: {prim.text}")
        self.setData(0, prim.ref)
        self._start = None

    def mousePressEvent(self, e):  # noqa: N802
        self._start = QPointF(self.pos())
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):  # noqa: N802
        super().mouseReleaseEvent(e)
        if self._start is not None and (self.pos() - self._start).manhattanLength() > 0.5:
            self.view.handleMoved.emit(self.ref, self.pos().x(), -self.pos().y())
        self._start = None


class DrawingView(QGraphicsView):
    elementClicked = Signal(str)
    handleMoved = Signal(str, float, float)
    measured = Signal(float)
    cursorMoved = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setMouseTracking(True)
        self.theme = "light"
        self.scene_data: Scene | None = None
        self.mode = "stm"
        self.visible_layers: set[str] = set(VIEW_LAYERS["stm"])
        self.selected_ref = ""
        self.highlight_critical = True
        self.handles_enabled = True
        self.measure_mode = False
        self._measure_pts: list[QPointF] = []
        self._measure_items: list = []
        self._panning = False
        self._pan_start = None
        self._fitted = False
        self.text_scale = 1.0
        self.banner = QLabel(self)
        self.banner.setStyleSheet("background: rgba(84,110,122,220); color: white; padding: 4px 10px;"
                                  "border-radius: 3px; font-weight: 600;")
        self.banner.hide()
        self.legend = QLabel(self)
        self.legend.setStyleSheet("background: rgba(255,255,255,210); color: #111; padding: 4px; border: 1px solid #aaa;")
        self.legend.hide()

    # ------------------------------------------------------------------
    def set_scene_data(self, scene: Scene, refit: bool = False) -> None:
        self.scene_data = scene
        self.render()
        if refit or not self._fitted:
            self.fit()
            self._fitted = True

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self.visible_layers = set(VIEW_LAYERS.get(mode, VIEW_LAYERS["stm"]))
        if not self.handles_enabled:
            self.visible_layers.discard("handles")
        self.render()

    def set_layer(self, layer: str, on: bool) -> None:
        if on:
            self.visible_layers.add(layer)
        else:
            self.visible_layers.discard(layer)
        self.render()

    def fit(self) -> None:
        if self.scene_data is None:
            return
        x0, y0, x1, y1 = self.scene_data.bounds
        self.fitInView(QRectF(x0, -y1, x1 - x0, y1 - y0), Qt.KeepAspectRatio)

    def select_ref(self, ref: str) -> None:
        self.selected_ref = ref
        self.render()

    # ------------------------------------------------------------------
    def _pen(self, prim: Prim, color: QColor | None = None, width: float | None = None) -> QPen:
        c = color or canvas_color(self.theme, prim.color)
        pen = QPen(c, width if width is not None else prim.width)
        pen.setCosmetic(True)
        if prim.dash:
            pen.setStyle(Qt.DashLine)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        return pen

    def _brush(self, prim: Prim) -> QBrush:
        if not prim.fill:
            return QBrush(Qt.NoBrush)
        c = QColor(canvas_color(self.theme, prim.fill))
        c.setAlphaF(max(0.0, min(1.0, prim.alpha)))
        return QBrush(c)

    def render(self) -> None:
        sc = self.scene()
        sc.clear()
        self._measure_items = []
        sc.setBackgroundBrush(QBrush(canvas_color(self.theme, "background")))
        data = self.scene_data
        if data is None:
            return
        if data.stale:
            self.banner.setText("Wyniki nieaktualne — uruchom obliczenia (F5). Rysunek pokazuje wyłącznie geometrię "
                                "z danych wejściowych.")
            self.banner.adjustSize()
            self.banner.move(10, 10)
            self.banner.show()
        else:
            self.banner.hide()
        if self.mode == "stress" and not data.stale:
            self.legend.setText("<b>η</b>: <span style='color:#2e7d32'>■</span> ≤ 0,5 &nbsp; "
                                "<span style='color:#f9a825'>■</span> ≤ 0,85 &nbsp; "
                                "<span style='color:#ef6c00'>■</span> ≤ 1,0 &nbsp; "
                                "<span style='color:#c62828'>■</span> > 1,0 &nbsp; "
                                "<span style='color:#e600e6'>●</span> krytyczny")
            self.legend.adjustSize()
            self.legend.move(10, self.viewport().height() - self.legend.height() - 10)
            self.legend.show()
        else:
            self.legend.hide()
        visible = set(self.visible_layers)
        if not self.handles_enabled:
            visible.discard("handles")
        for prim in data.prims:
            if prim.layer not in visible:
                continue
            if prim.text == "krytyczny" and not self.highlight_critical:
                continue
            self._draw(sc, prim)
        if self.selected_ref:
            for prim in data.prims:
                if prim.ref == self.selected_ref and prim.layer in visible and prim.kind in ("line", "polyline",
                                                                                              "polygon", "circle"):
                    hp = Prim(prim.kind, prim.layer, prim.pts, color="select", width=max(prim.width + 3, 4),
                              radius=prim.radius)
                    item = self._draw(sc, hp)
                    if item is not None:
                        item.setZValue(50)

    def _draw(self, sc: QGraphicsScene, prim: Prim):
        k = prim.kind
        item = None
        if k in ("line", "polyline") and len(prim.pts) >= 2:
            path = QPainterPath(_p(prim.pts[0]))
            for q in prim.pts[1:]:
                path.lineTo(_p(q))
            item = sc.addPath(path, self._pen(prim))
            if prim.alpha < 1.0:
                item.setOpacity(prim.alpha)
        elif k == "polygon" and len(prim.pts) >= 3:
            item = sc.addPolygon(QPolygonF([_p(q) for q in prim.pts]), self._pen(prim), self._brush(prim))
        elif k == "circle":
            r = prim.radius
            c = _p(prim.pts[0])
            item = sc.addEllipse(c.x() - r, c.y() - r, 2 * r, 2 * r, self._pen(prim), self._brush(prim))
        elif k == "arc":
            c = _p(prim.pts[0])
            r = prim.radius
            path = QPainterPath()
            rect = QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r)
            path.arcMoveTo(rect, prim.angles[0])
            path.arcTo(rect, prim.angles[0], prim.angles[1])
            item = sc.addPath(path, self._pen(prim))
        elif k == "arrow" and len(prim.pts) == 2:
            item = self._arrow(sc, prim)
        elif k == "text":
            item = self._text(sc, prim.text, prim.pts[0], prim.color, prim.size, prim.anchor)
        elif k == "dim":
            item = self._dim(sc, prim)
        elif k == "handle":
            item = HandleItem(self, prim, canvas_color(self.theme, prim.color))
            sc.addItem(item)
            return item
        if item is not None:
            item.setData(0, prim.ref)
            if prim.ref:
                item.setToolTip(prim.ref.split(":", 1)[-1])
        return item

    def _text(self, sc, text, pt, color, size, anchor="c"):
        it = QGraphicsSimpleTextItem(text)
        f = QFont()
        f.setPointSizeF(size * self.text_scale)
        it.setFont(f)
        it.setBrush(QBrush(canvas_color(self.theme, color if color else "text")))
        it.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        br = it.boundingRect()
        dx = {"c": -br.width() / 2, "l": 0.0, "r": -br.width()}.get(anchor, -br.width() / 2)
        it.setTransform(QTransform.fromTranslate(dx, -br.height() / 2))
        it.setPos(_p(pt))
        it.setZValue(20)
        sc.addItem(it)
        return it

    def _arrow(self, sc, prim: Prim):
        a, b = _p(prim.pts[0]), _p(prim.pts[1])
        path = QPainterPath(a)
        path.lineTo(b)
        dx, dy = b.x() - a.x(), b.y() - a.y()
        L = math.hypot(dx, dy) or 1.0
        ux, uy = dx / L, dy / L
        hl = min(0.3 * L, 45.0)
        hw = hl * 0.45
        p1 = QPointF(b.x() - ux * hl - uy * hw, b.y() - uy * hl + ux * hw)
        p2 = QPointF(b.x() - ux * hl + uy * hw, b.y() - uy * hl - ux * hw)
        item = sc.addPath(path, self._pen(prim))
        head = sc.addPolygon(QPolygonF([b, p1, p2]), self._pen(prim, width=1.0),
                             QBrush(canvas_color(self.theme, prim.color)))
        head.setData(0, prim.ref)
        return item

    def _dim(self, sc, prim: Prim):
        (x1, y1), (x2, y2) = prim.pts
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L, dx / L
        o = prim.offset
        q1 = (x1 + nx * o, y1 + ny * o)
        q2 = (x2 + nx * o, y2 + ny * o)
        pen = self._pen(prim)
        path = QPainterPath(_p((x1, y1)))
        path.lineTo(_p((x1 + nx * (o + math.copysign(8, o or 1)), y1 + ny * (o + math.copysign(8, o or 1)))))
        path.moveTo(_p((x2, y2)))
        path.lineTo(_p((x2 + nx * (o + math.copysign(8, o or 1)), y2 + ny * (o + math.copysign(8, o or 1)))))
        path.moveTo(_p(q1))
        path.lineTo(_p(q2))
        t = 10.0
        ux, uy = dx / L, dy / L
        for q in (q1, q2):
            path.moveTo(_p((q[0] - (ux + nx) * t * 0.7, q[1] - (uy + ny) * t * 0.7)))
            path.lineTo(_p((q[0] + (ux + nx) * t * 0.7, q[1] + (uy + ny) * t * 0.7)))
        item = sc.addPath(path, pen)
        mid = ((q1[0] + q2[0]) / 2 + nx * 14 * math.copysign(1, o or 1), (q1[1] + q2[1]) / 2 + ny * 14 *
               math.copysign(1, o or 1))
        self._text(sc, prim.text, mid, "dim", prim.size)
        return item

    # --- interakcja ----------------------------------------------------
    def wheelEvent(self, e):  # noqa: N802
        f = 1.18 if e.angleDelta().y() > 0 else 1 / 1.18
        self.scale(f, f)

    def mousePressEvent(self, e):  # noqa: N802
        if e.button() in (Qt.MiddleButton, Qt.RightButton) or (e.button() == Qt.LeftButton and
                                                               e.modifiers() & Qt.ShiftModifier):
            self._panning = True
            self._pan_start = e.position()
            self.setCursor(Qt.ClosedHandCursor)
            e.accept()
            return
        if e.button() == Qt.LeftButton:
            item = self.itemAt(e.position().toPoint())
            if isinstance(item, HandleItem):
                super().mousePressEvent(e)
                return
            if self.measure_mode:
                self._measure_click(self.mapToScene(e.position().toPoint()))
                return
            ref = self._ref_at(e.position().toPoint())
            if ref:
                self.selected_ref = ref
                self.render()
                self.elementClicked.emit(ref)
            return
        super().mousePressEvent(e)

    def _ref_at(self, pos) -> str:
        for it in self.items(pos):
            ref = it.data(0)
            if ref and not str(ref).startswith("geom:"):
                return str(ref)
        for it in self.items(pos):
            ref = it.data(0)
            if ref:
                return str(ref)
        return ""

    def mouseMoveEvent(self, e):  # noqa: N802
        if self._panning and self._pan_start is not None:
            d = e.position() - self._pan_start
            self._pan_start = e.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(d.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(d.y()))
            return
        sp = self.mapToScene(e.position().toPoint())
        self.cursorMoved.emit(sp.x(), -sp.y())
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):  # noqa: N802
        if self._panning:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            return
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):  # noqa: N802
        self.fit()

    def resizeEvent(self, e):  # noqa: N802
        super().resizeEvent(e)
        if self.legend.isVisible():
            self.legend.move(10, self.viewport().height() - self.legend.height() - 10)

    def _measure_click(self, sp: QPointF) -> None:
        self._measure_pts.append(sp)
        sc = self.scene()
        pen = QPen(canvas_color(self.theme, "measure"), 2)
        pen.setCosmetic(True)
        dot = sc.addEllipse(sp.x() - 4, sp.y() - 4, 8, 8, pen)
        self._measure_items.append(dot)
        if len(self._measure_pts) == 2:
            a, b = self._measure_pts
            sc.addLine(a.x(), a.y(), b.x(), b.y(), pen)
            d = math.hypot(b.x() - a.x(), b.y() - a.y())
            self._text(sc, f"{d:.1f} mm  (Δx = {abs(b.x() - a.x()):.1f}, Δy = {abs(b.y() - a.y()):.1f})",
                       ((a.x() + b.x()) / 2, -(a.y() + b.y()) / 2 + 25), "measure", 9)
            self._measure_pts = []
            self.measured.emit(d)
