"""Jednostki, konwersje i kontrola wymiarów.

Jednostki bazowe silnika obliczeniowego (stosowane wewnętrznie we WSZYSTKICH
modułach obliczeniowych):

* siła          — N
* długość       — mm
* naprężenie    — MPa = N/mm²
* pole          — mm²
* moment        — N·mm
* kąt           — stopnie (w rekordach wyników), radiany w obliczeniach

Klasa :class:`Q` realizuje prostą analizę wymiarową (wykładniki siły i
długości). Jest używana w modułach sprawdzeń do kontroli spójności jednostek
wzorów — błąd wymiaru zgłasza wyjątek :class:`UnitError`.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math


class UnitError(ValueError):
    """Niezgodność jednostek / wymiarów."""


class Kind(str, Enum):
    FORCE = "force"
    LENGTH = "length"
    STRESS = "stress"
    AREA = "area"
    MOMENT = "moment"
    ANGLE = "angle"
    RATIO = "ratio"
    MASS = "mass"
    VOLUME = "volume"
    NONE = "none"


# Wykładniki wymiarów (siła, długość) dla każdej wielkości.
DIMS: dict[Kind, tuple[int, int]] = {
    Kind.FORCE: (1, 0),
    Kind.LENGTH: (0, 1),
    Kind.STRESS: (1, -2),
    Kind.AREA: (0, 2),
    Kind.MOMENT: (1, 1),
    Kind.ANGLE: (0, 0),
    Kind.RATIO: (0, 0),
    Kind.NONE: (0, 0),
    Kind.VOLUME: (0, 3),
}

# Mnożniki: wartość_w_bazie = wartość_w_jednostce * mnożnik
UNITS: dict[Kind, dict[str, float]] = {
    Kind.FORCE: {"N": 1.0, "kN": 1.0e3, "MN": 1.0e6},
    Kind.LENGTH: {"mm": 1.0, "cm": 10.0, "m": 1000.0},
    Kind.STRESS: {"MPa": 1.0, "N/mm²": 1.0, "kPa": 1.0e-3, "GPa": 1.0e3, "kN/cm²": 10.0},
    Kind.AREA: {"mm²": 1.0, "cm²": 100.0, "m²": 1.0e6},
    Kind.MOMENT: {"N·mm": 1.0, "kN·m": 1.0e6, "kN·cm": 1.0e4},
    Kind.ANGLE: {"°": 1.0},
    Kind.RATIO: {"-": 1.0, "%": 0.01},
    Kind.MASS: {"kg": 1.0, "t": 1000.0},
    Kind.VOLUME: {"mm³": 1.0, "dm³": 1.0e6, "m³": 1.0e9},
    Kind.NONE: {"": 1.0},
}

BASE_UNIT: dict[Kind, str] = {
    Kind.FORCE: "N",
    Kind.LENGTH: "mm",
    Kind.STRESS: "MPa",
    Kind.AREA: "mm²",
    Kind.MOMENT: "N·mm",
    Kind.ANGLE: "°",
    Kind.RATIO: "-",
    Kind.MASS: "kg",
    Kind.VOLUME: "mm³",
    Kind.NONE: "",
}


def to_base(value: float, kind: Kind, unit: str) -> float:
    """Przelicza wartość z jednostki ``unit`` na jednostkę bazową."""
    try:
        return float(value) * UNITS[kind][unit]
    except KeyError as exc:  # pragma: no cover - błąd programisty
        raise UnitError(f"Nieznana jednostka '{unit}' dla wielkości {kind.value}") from exc


def from_base(value: float, kind: Kind, unit: str) -> float:
    """Przelicza wartość z jednostki bazowej na jednostkę ``unit``."""
    try:
        return float(value) / UNITS[kind][unit]
    except KeyError as exc:  # pragma: no cover
        raise UnitError(f"Nieznana jednostka '{unit}' dla wielkości {kind.value}") from exc


@dataclass
class DisplayUnits:
    """Jednostki prezentacji (GUI / raport). Obliczenia zawsze w bazie."""

    force: str = "kN"
    length: str = "mm"
    stress: str = "MPa"
    area: str = "mm²"
    moment: str = "kN·m"

    def unit_for(self, kind: Kind) -> str:
        return {
            Kind.FORCE: self.force,
            Kind.LENGTH: self.length,
            Kind.STRESS: self.stress,
            Kind.AREA: self.area,
            Kind.MOMENT: self.moment,
        }.get(kind, BASE_UNIT.get(kind, ""))


DISPLAY = DisplayUnits()


def fmt(value: float | None, kind: Kind | str, prec: int | None = None,
        units: DisplayUnits | None = None, with_unit: bool = True) -> str:
    """Formatuje wartość bazową w jednostce prezentacji."""
    if value is None:
        return "—"
    kind = Kind(kind)
    units = units or DISPLAY
    unit = units.unit_for(kind)
    v = from_base(value, kind, unit) if kind in UNITS and unit in UNITS[kind] else value
    if prec is None:
        prec = _default_precision(kind, unit, v)
    if not math.isfinite(v):
        txt = "∞" if v > 0 else "-∞"
    else:
        txt = f"{v:.{prec}f}"
    return f"{txt} {unit}".strip() if with_unit and unit not in ("-", "") else txt


def _default_precision(kind: Kind, unit: str, v: float) -> int:
    if kind == Kind.FORCE:
        return 1 if unit == "kN" else (0 if unit == "N" else 3)
    if kind == Kind.LENGTH:
        return 0 if unit == "mm" else (1 if unit == "cm" else 3)
    if kind == Kind.STRESS:
        return 2
    if kind == Kind.AREA:
        return 0 if unit == "mm²" else 2
    if kind == Kind.MOMENT:
        return 2
    if kind == Kind.ANGLE:
        return 1
    if kind == Kind.RATIO:
        return 3
    return 3


# ---------------------------------------------------------------------------
# Analiza wymiarowa
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Q:
    """Wielkość fizyczna w jednostkach bazowych z wykładnikami (siła, długość).

    Przykład::

        T = Q(400e3, Kind.FORCE)
        fyd = Q(434.8, Kind.STRESS)
        As = (T / fyd).expect(Kind.AREA)
    """

    value: float
    dims: tuple[int, int]

    def __init__(self, value: float, kind_or_dims: Kind | tuple[int, int] = Kind.NONE):
        object.__setattr__(self, "value", float(value))
        if isinstance(kind_or_dims, Kind):
            object.__setattr__(self, "dims", DIMS[kind_or_dims])
        else:
            object.__setattr__(self, "dims", tuple(kind_or_dims))

    # --- arytmetyka -------------------------------------------------------
    def _coerce(self, other) -> "Q":
        if isinstance(other, Q):
            return other
        if isinstance(other, (int, float)):
            return Q(float(other), (0, 0))
        raise TypeError(f"Nieobsługiwany typ: {type(other)!r}")

    def __add__(self, other):
        o = self._coerce(other)
        if o.dims != self.dims:
            raise UnitError(f"Dodawanie wielkości o różnych wymiarach {self.dims} + {o.dims}")
        return Q(self.value + o.value, self.dims)

    __radd__ = __add__

    def __sub__(self, other):
        o = self._coerce(other)
        if o.dims != self.dims:
            raise UnitError(f"Odejmowanie wielkości o różnych wymiarach {self.dims} - {o.dims}")
        return Q(self.value - o.value, self.dims)

    def __rsub__(self, other):
        return self._coerce(other).__sub__(self)

    def __mul__(self, other):
        o = self._coerce(other)
        return Q(self.value * o.value, (self.dims[0] + o.dims[0], self.dims[1] + o.dims[1]))

    __rmul__ = __mul__

    def __truediv__(self, other):
        o = self._coerce(other)
        return Q(self.value / o.value, (self.dims[0] - o.dims[0], self.dims[1] - o.dims[1]))

    def __rtruediv__(self, other):
        return self._coerce(other).__truediv__(self)

    def __pow__(self, p: float):
        if self.dims != (0, 0) and not float(p).is_integer() and p != 0.5:
            raise UnitError("Potęga niecałkowita wielkości wymiarowej")
        if p == 0.5:
            if self.dims[0] % 2 or self.dims[1] % 2:
                raise UnitError(f"Pierwiastek z wymiaru {self.dims}")
            return Q(math.sqrt(self.value), (self.dims[0] // 2, self.dims[1] // 2))
        p = int(p)
        return Q(self.value ** p, (self.dims[0] * p, self.dims[1] * p))

    def __neg__(self):
        return Q(-self.value, self.dims)

    def __lt__(self, other):
        o = self._coerce(other)
        self._same(o)
        return self.value < o.value

    def __le__(self, other):
        o = self._coerce(other)
        self._same(o)
        return self.value <= o.value

    def _same(self, o: "Q") -> None:
        if o.dims != self.dims:
            raise UnitError(f"Porównanie wielkości o różnych wymiarach {self.dims} vs {o.dims}")

    def expect(self, kind: Kind) -> "Q":
        """Sprawdza, czy wynik ma wymiar ``kind`` — w przeciwnym razie UnitError."""
        if self.dims != DIMS[kind]:
            raise UnitError(f"Oczekiwano wymiaru {kind.value} {DIMS[kind]}, otrzymano {self.dims}")
        return self

    @property
    def v(self) -> float:
        return self.value


def qmin(*qs: Q) -> Q:
    d = qs[0].dims
    for q in qs:
        if q.dims != d:
            raise UnitError("min() z wielkości o różnych wymiarach")
    return Q(min(q.value for q in qs), d)


def qmax(*qs: Q) -> Q:
    d = qs[0].dims
    for q in qs:
        if q.dims != d:
            raise UnitError("max() z wielkości o różnych wymiarach")
    return Q(max(q.value for q in qs), d)


def bar_area(phi: float) -> float:
    """Pole przekroju pręta o średnicy ``phi`` [mm] → [mm²]."""
    return math.pi * phi * phi / 4.0


def bar_unit_mass(phi: float) -> float:
    """Masa jednostkowa pręta [kg/m] przy gęstości stali 7850 kg/m³."""
    return bar_area(phi) * 1e-6 * 7850.0
