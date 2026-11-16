"""Uruchomienie aplikacji (punkt wejścia także dla PyInstaller)."""
import sys

from kwst.gui.app import run_gui

if __name__ == "__main__":
    if "--selftest" in sys.argv:
        from kwst.selftest import run_selftest
        sys.exit(run_selftest())
    sys.exit(run_gui(sys.argv))
