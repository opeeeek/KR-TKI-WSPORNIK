"""Uruchomienie aplikacji desktopowej."""
from __future__ import annotations

import logging
import sys
import traceback

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from ..core.logging_setup import setup_logging
from ..core.units import DISPLAY
from ..project_io import app_data_dir
from ..version import APP_NAME, __version__
from .i18n import set_language
from .themes import apply_theme


def _excepthook(exc_type, exc, tb):
    logging.getLogger("kwst").critical("Nieobsłużony wyjątek", exc_info=(exc_type, exc, tb))
    app = QApplication.instance()
    if app is not None:
        QMessageBox.critical(None, APP_NAME, "Wystąpił nieoczekiwany błąd. Szczegóły zapisano w dzienniku.\n\n"
                             + "".join(traceback.format_exception_only(exc_type, exc)))


def create_app(argv=None) -> QApplication:
    app = QApplication.instance() or QApplication(list(argv or sys.argv))
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("KrotkiWspornikST")
    return app


def run_gui(argv=None) -> int:
    log_path = setup_logging(app_data_dir() / "logs")
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = create_app(argv)
    sys.excepthook = _excepthook
    settings = QSettings("KrotkiWspornikST", "KWST")
    set_language(str(settings.value("lang", "pl")))
    for k in ("force", "length", "stress", "moment"):
        val = settings.value(f"unit_{k}")
        if val:
            setattr(DISPLAY, k, str(val))
    apply_theme(app, str(settings.value("theme", "light")), float(settings.value("scale", 1.0)))
    from pathlib import Path
    icon = Path(__file__).resolve().parent.parent / "resources" / "icon.png"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))
    from .main_window import MainWindow
    w = MainWindow(settings=settings)
    w.canvas.text_scale = float(settings.value("scale", 1.0))
    args = [a for a in (argv or sys.argv)[1:] if not a.startswith("-")]
    if args:
        w.open_project(args[0])
    w.show()
    logging.getLogger("kwst").info("Start %s %s (log: %s)", APP_NAME, __version__, log_path)
    return app.exec()
