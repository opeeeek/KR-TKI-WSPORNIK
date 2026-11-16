"""Generuje ikonę aplikacji (PNG + ICO) rysowaną programowo (bez zewnętrznych grafik)."""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QPointF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPen, QPolygonF, QBrush  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def draw(size: int) -> QImage:
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    s = size / 64.0
    p.setBrush(QBrush(QColor("#1f3b5c")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(0, 0, size, size, 12 * s, 12 * s)
    p.setBrush(QBrush(QColor("#d8dce2")))
    p.drawRect(int(8 * s), int(6 * s), int(14 * s), int(52 * s))                     # słup
    p.drawPolygon(QPolygonF([QPointF(22 * s, 18 * s), QPointF(56 * s, 18 * s), QPointF(56 * s, 30 * s),
                             QPointF(22 * s, 44 * s)]))                                 # wspornik
    pen = QPen(QColor("#4a86e8"), 3.2 * s)
    p.setPen(pen)
    p.drawLine(QPointF(12 * s, 22 * s), QPointF(48 * s, 22 * s))                      # cięgno
    pen = QPen(QColor("#e8584f"), 3.2 * s, Qt.DashLine)
    p.setPen(pen)
    p.drawLine(QPointF(48 * s, 22 * s), QPointF(24 * s, 41 * s))                      # krzyżulec
    p.setPen(QPen(QColor("#ffffff"), 1.4 * s))
    p.setBrush(QBrush(QColor("#ffffff")))
    for x, y in ((48, 22), (24, 41)):
        p.drawEllipse(QPointF(x * s, y * s), 2.6 * s, 2.6 * s)
    p.setPen(QPen(QColor("#3fb950"), 3 * s))
    p.drawLine(QPointF(48 * s, 4 * s), QPointF(48 * s, 15 * s))                       # obciążenie
    p.end()
    return img


def main():
    app = QGuiApplication(sys.argv)  # noqa: F841
    res = ROOT / "kwst" / "resources"
    draw(256).save(str(res / "icon.png"))
    ok = draw(256).save(str(ROOT / "packaging" / "icon.ico"))
    print("icon.png zapisano; icon.ico:", "OK" if ok else "brak wtyczki ICO (użyj icon.png)")


if __name__ == "__main__":
    main()
