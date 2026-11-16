"""Zapis/odczyt projektów (.kwst — JSON), autozapis i biblioteka typowych wsporników."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from .core.model import Project, Variant, SCHEMA_VERSION
from .core.serialization import to_dict, from_dict
from .version import __version__

EXT = ".kwst"


class ProjectFileError(ValueError):
    pass


def save_project(project: Project, path: str | os.PathLike) -> None:
    data = {"format": "KROTKI_WSPORNIK_ST", "program_version": __version__, "saved": time.strftime("%Y-%m-%d %H:%M:%S"),
            "project": to_dict(project)}
    p = Path(path)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def load_project(path: str | os.PathLike) -> Project:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProjectFileError(f"Nie można odczytać pliku projektu: {exc}") from exc
    if not isinstance(data, dict) or data.get("format") != "KROTKI_WSPORNIK_ST":
        raise ProjectFileError("Plik nie jest projektem programu KRÓTKI WSPORNIK ST.")
    pd = data.get("project", {})
    ver = int(pd.get("schema_version", 0))
    if ver > SCHEMA_VERSION:
        raise ProjectFileError(f"Plik zapisany w nowszej wersji schematu ({ver}) — zaktualizuj program.")
    try:
        return from_dict(Project, pd)
    except (TypeError, ValueError, KeyError) as exc:
        raise ProjectFileError(f"Niepoprawna struktura danych projektu: {exc}") from exc


def app_data_dir() -> Path:
    base = os.environ.get("APPDATA") or os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    d = Path(base) / "KrotkiWspornikST"
    d.mkdir(parents=True, exist_ok=True)
    return d


def autosave_dir() -> Path:
    d = app_data_dir() / "autosave"
    d.mkdir(parents=True, exist_ok=True)
    return d


def autosave(project: Project, tag: str = "biezacy") -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in tag)[:60] or "projekt"
    path = autosave_dir() / f"{safe}{EXT}.autosave"
    save_project(project, path)
    return path


def latest_autosave() -> Path | None:
    files = sorted(autosave_dir().glob(f"*{EXT}.autosave"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


@dataclass
class LibraryItem:
    key: str
    title: str
    description: str
    variant: Variant


def library_dir() -> Path:
    return Path(__file__).resolve().parent / "resources" / "library"


def load_library() -> list[LibraryItem]:
    items: list[LibraryItem] = []
    for f in sorted(library_dir().glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            items.append(LibraryItem(f.stem, d["title"], d.get("description", ""), from_dict(Variant, d["variant"])))
        except (OSError, KeyError, ValueError, TypeError):
            continue
    return items
