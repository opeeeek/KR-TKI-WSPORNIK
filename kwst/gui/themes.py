"""Motywy kolorystyczne (jasny / ciemny) — paleta Qt, arkusz stylów i kolory rysunku."""
from __future__ import annotations

from PySide6.QtGui import QColor, QPalette

from ..palette import CANVAS, STATUS_COLORS, VERDICT_COLORS  # noqa: E402


def canvas_color(theme: str, key: str) -> QColor:
    pal = CANVAS.get(theme, CANVAS["light"])
    return QColor(pal.get(key, pal["line"]))


def apply_theme(app, theme: str, scale: float = 1.0) -> None:
    app.setStyle("Fusion")
    pal = QPalette()
    if theme == "dark":
        base, alt, text, win, btn, hl = "#1e2227", "#262b31", "#e6e6e6", "#23272e", "#2d333b", "#2f81f7"
    else:
        base, alt, text, win, btn, hl = "#ffffff", "#f3f5f7", "#15191e", "#eef0f3", "#e7eaee", "#1f6feb"
    pal.setColor(QPalette.Window, QColor(win))
    pal.setColor(QPalette.WindowText, QColor(text))
    pal.setColor(QPalette.Base, QColor(base))
    pal.setColor(QPalette.AlternateBase, QColor(alt))
    pal.setColor(QPalette.ToolTipBase, QColor(base))
    pal.setColor(QPalette.ToolTipText, QColor(text))
    pal.setColor(QPalette.Text, QColor(text))
    pal.setColor(QPalette.Button, QColor(btn))
    pal.setColor(QPalette.ButtonText, QColor(text))
    pal.setColor(QPalette.Highlight, QColor(hl))
    pal.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    pal.setColor(QPalette.PlaceholderText, QColor("#8a8f98"))
    pal.setColor(QPalette.Disabled, QPalette.Text, QColor("#8a8f98"))
    pal.setColor(QPalette.Disabled, QPalette.WindowText, QColor("#8a8f98"))
    app.setPalette(pal)
    f = app.font()
    f.setPointSizeF(9.0 * scale)
    app.setFont(f)
    border = "#3a4049" if theme == "dark" else "#c9ced6"
    app.setStyleSheet(f"""
        QGroupBox {{ font-weight: 600; border: 1px solid {border}; border-radius: 4px; margin-top: 10px;
                     padding-top: 6px; }}
        QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 3px; }}
        QDockWidget::title {{ padding: 4px; font-weight: 600; }}
        QTreeWidget::item {{ padding: 2px; }}
        QToolBar {{ spacing: 3px; }}
    """)
