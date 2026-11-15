"""Wspólne narzędzia do budowy rekordów sprawdzeń (formatowanie podstawień)."""
from __future__ import annotations

from .core.results import Check, Basis, CheckStatus
from .core.units import Kind


def n(v: float, p: int = 2) -> str:
    """Liczba w formacie polskim (przecinek dziesiętny)."""
    if v is None:
        return "—"
    s = f"{v:.{p}f}"
    return s.replace(".", ",")


def kN(v: float, p: int = 1) -> str:
    return n(v / 1e3, p) + " kN"


def mm(v: float, p: int = 0) -> str:
    return n(v, p) + " mm"


def mm2(v: float, p: int = 0) -> str:
    return n(v, p) + " mm²"


def MPa(v: float, p: int = 2) -> str:
    return n(v, p) + " MPa"


def make(id: str, group: str, title: str, clause: str, basis: Basis, formula: str, symbols: dict,
         substitution: str, E_d: float | None, R_d: float | None, kind: Kind, combination: str = "",
         element_ref: str = "", notes: list[str] | None = None, recommendation: bool = False,
         E_label: str = "E_d", R_label: str = "R_d", status: CheckStatus | None = None,
         conclusion: str = "") -> Check:
    c = Check(id=id, group=group, title=title, clause=clause, basis=basis, formula=formula, symbols=symbols,
              substitution=substitution, E_d=E_d, R_d=R_d, kind=kind, combination=combination,
              element_ref=element_ref, notes=list(notes or []), E_label=E_label, R_label=R_label,
              conclusion=conclusion)
    if status is not None:
        c.status = status
        if E_d is not None and R_d is not None and R_d > 0:
            c.eta = E_d / R_d
        if not c.conclusion:
            c.conclusion = {
                CheckStatus.NA: "Nie dotyczy.",
                CheckStatus.VERIFY: "Wymaga osobnej weryfikacji poza zakresem programu.",
                CheckStatus.OK: "Warunek spełniony.",
                CheckStatus.FAIL: "Warunek NIE jest spełniony.",
            }[status]
        return c
    return c.evaluate(recommendation_only=recommendation)


SIDE_NAME = {"R": "prawy", "L": "lewy"}
