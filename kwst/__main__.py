"""Punkt wejścia: ``python -m kwst`` uruchamia aplikację desktopową."""
import sys


def main() -> int:
    if "--selftest" in sys.argv:
        from kwst.selftest import run_selftest
        return run_selftest()
    from kwst.gui.app import run_gui

    return run_gui(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
