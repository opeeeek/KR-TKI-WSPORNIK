"""Konfiguracja rejestrowania zdarzeń i błędów (plik w katalogu danych aplikacji + konsola)."""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path


def setup_logging(log_dir: Path | None = None, level: int = logging.INFO) -> Path | None:
    root = logging.getLogger()
    if any(getattr(h, "_kwst", False) for h in root.handlers):
        return None
    root.setLevel(level)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    sh.setLevel(logging.WARNING)
    sh._kwst = True
    root.addHandler(sh)
    path = None
    if log_dir is not None:
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            path = log_dir / "kwst.log"
            fh = logging.handlers.RotatingFileHandler(path, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
            fh.setFormatter(fmt)
            fh._kwst = True
            root.addHandler(fh)
        except OSError:
            path = None
    return path
