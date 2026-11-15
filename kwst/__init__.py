"""KRÓTKI WSPORNIK ST — projektowanie krótkich wsporników żelbetowych metodą
Strut-and-Tie wg PN-EN 1992-1-1.

Pakiet jest podzielony na silnik obliczeniowy (moduły ``*_engine``, ``stm_*``,
``*_checks``, ``analysis``) niezależny od interfejsu oraz warstwę GUI
(``kwst.gui``), raportowania (``kwst.report_engine``) i wizualizacji
(``kwst.visualization_engine``).
"""
from .version import __version__, APP_NAME

__all__ = ["__version__", "APP_NAME"]
