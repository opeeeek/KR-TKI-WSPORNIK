"""Struktury wyników: sprawdzenia, komunikaty, werdykt."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .units import Kind

ETA_TOL = 1e-9


class CheckStatus(str, Enum):
    OK = "SPEŁNIONO"
    FAIL = "NIE SPEŁNIONO"
    VERIFY = "WYMAGA OSOBNEJ WERYFIKACJI"
    NA = "NIE DOTYCZY"

    @property
    def en(self) -> str:
        return {"SPEŁNIONO": "SATISFIED", "NIE SPEŁNIONO": "NOT SATISFIED",
                "WYMAGA OSOBNEJ WERYFIKACJI": "REQUIRES SEPARATE VERIFICATION",
                "NIE DOTYCZY": "NOT APPLICABLE"}[self.value]


class Basis(str, Enum):
    """Charakter podstawy sprawdzenia."""
    NORMATIVE = "normatywne"
    INFORMATIVE = "informacyjne (zał. J EN 1992-1-1)"
    ENGINEERING = "zalecenie inżynierskie"
    MODEL = "kontrola modelu"


class Level(str, Enum):
    ERROR = "BŁĄD"
    WARNING = "OSTRZEŻENIE"
    INFO = "INFORMACJA"


@dataclass
class Message:
    level: Level
    text: str
    ref: str = ""
    source: str = ""


@dataclass
class Check:
    id: str
    group: str
    title: str
    clause: str
    basis: Basis
    formula: str = ""
    symbols: dict[str, str] = field(default_factory=dict)
    substitution: str = ""
    E_d: Optional[float] = None
    R_d: Optional[float] = None
    kind: Kind = Kind.NONE
    eta: Optional[float] = None
    status: CheckStatus = CheckStatus.NA
    conclusion: str = ""
    combination: str = ""
    element_ref: str = ""
    notes: list[str] = field(default_factory=list)
    E_label: str = "E_d"
    R_label: str = "R_d"

    def evaluate(self, recommendation_only: bool = False) -> "Check":
        """Wyznacza η i status na podstawie E_d / R_d.

        Dla zaleceń inżynierskich niespełnienie skutkuje statusem
        WYMAGA OSOBNEJ WERYFIKACJI (nie jest to wymóg normowy)."""
        if self.E_d is None or self.R_d is None:
            return self
        if self.R_d <= 0.0:
            self.eta = float("inf") if self.E_d > 0 else 0.0
        else:
            self.eta = max(self.E_d, 0.0) / self.R_d
        ok = self.eta <= 1.0 + ETA_TOL
        if ok:
            self.status = CheckStatus.OK
        else:
            self.status = CheckStatus.VERIFY if recommendation_only else CheckStatus.FAIL
        if not self.conclusion:
            if ok:
                self.conclusion = "Warunek spełniony."
            elif recommendation_only:
                self.conclusion = "Zalecenie niespełnione — wymagana ocena projektanta."
            else:
                self.conclusion = "Warunek NIE jest spełniony."
        return self


@dataclass
class Verdict:
    code: str            # FAIL | PASS_SCOPE | CONDITIONAL | BLOCKED
    title: str
    text: str
    positive: bool

    @staticmethod
    def build(checks: list[Check], errors: list[Message], ndp_confirmed: bool) -> "Verdict":
        fails = [c for c in checks if c.status == CheckStatus.FAIL]
        verify = [c for c in checks if c.status == CheckStatus.VERIFY]
        if errors:
            return Verdict("BLOCKED", "OBLICZENIA ZABLOKOWANE",
                           "Wykryto błędy krytyczne danych lub modelu obliczeniowego "
                           f"({len(errors)}). Wynik pozytywny jest niedozwolony.", False)
        model_verify = [c for c in verify if c.group == "Model"]
        if model_verify:
            extra = (f" Dodatkowo {len(fails)} sprawdzeń nie jest spełnionych w modelu informacyjnym." if fails else "")
            return Verdict("OUT_OF_SCOPE", "MODEL POZA ZAKRESEM STOSOWANIA",
                           "Przyjęty model obliczeniowy (J.3) nie jest właściwy dla tej geometrii / obciążenia "
                           f"({', '.join(c.id for c in model_verify)}). Wymagana alternatywna metoda projektowania — "
                           "program jej nie wykonuje; pozytywny wniosek ogólny nie może zostać sformułowany." + extra,
                           False)
        if fails:
            return Verdict("FAIL", "NIE SPEŁNIONO",
                           f"Co najmniej jedno sprawdzenie nie jest spełnione ({len(fails)}). "
                           "Wspornik w obecnej postaci nie może zostać przyjęty.", False)
        txt = ("Wszystkie sprawdzenia objęte zakresem programu są spełnione. "
               f"Pozycje wymagające osobnej weryfikacji: {len(verify)} — wymienione w zestawieniu; "
               "wynik lokalnego modelu STM nie potwierdza nośności słupa, połączenia ani całej konstrukcji.")
        if not ndp_confirmed:
            return Verdict("CONDITIONAL", "SPEŁNIONO WARUNKOWO",
                           txt + " Parametry NDP nie zostały potwierdzone przez projektanta — wynik warunkowy.",
                           False)
        return Verdict("PASS_SCOPE", "SPEŁNIONO W ZAKRESIE PROGRAMU", txt, True)
