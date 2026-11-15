"""Punkt wejścia: ``python -m kwst`` uruchamia aplikację desktopową."""
import sys


def main() -> int:
    from kwst.gui.app import run_gui

    return run_gui(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
