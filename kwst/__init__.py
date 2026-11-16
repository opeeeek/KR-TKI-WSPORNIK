"""KRÓTKI WSPORNIK ST — projektowanie krótkich wsporników żelbetowych metodą
Strut-and-Tie wg PN-EN 1992-1-1.

Silnik referencyjny (Python): moduły ``*_engine``, ``stm_*``, ``*_checks``, ``analysis``, raporty
(``kwst.report_engine``) i wizualizacja (``kwst.visualization_engine``). Program dla użytkownika
(KrotkiWspornikST.exe i strona web) korzysta z portu silnika w JavaScript (katalog ``web/``),
porównywanego z tym silnikiem w testach krzyżowych.
"""
from .version import __version__, APP_NAME

__all__ = ["__version__", "APP_NAME"]
