import math
import pytest

from kwst.core.units import Q, Kind, UnitError, to_base, from_base, fmt, bar_area, bar_unit_mass


def test_conversions_roundtrip():
    for kind, unit, val in [(Kind.FORCE, "kN", 12.5), (Kind.LENGTH, "cm", 3.2), (Kind.LENGTH, "m", 0.45),
                            (Kind.STRESS, "MPa", 21.4), (Kind.MOMENT, "kN·m", 80.0), (Kind.AREA, "cm²", 6.28)]:
        assert from_base(to_base(val, kind, unit), kind, unit) == pytest.approx(val)
    assert to_base(1.0, Kind.FORCE, "kN") == 1000.0
    assert to_base(1.0, Kind.LENGTH, "m") == 1000.0
    assert to_base(1.0, Kind.MOMENT, "kN·m") == 1e6


def test_dimensional_analysis():
    T = Q(400e3, Kind.FORCE)
    fyd = Q(434.78, Kind.STRESS)
    As = (T / fyd).expect(Kind.AREA)
    assert As.v == pytest.approx(920.0, rel=1e-3)
    with pytest.raises(UnitError):
        (T / fyd).expect(Kind.FORCE)
    with pytest.raises(UnitError):
        _ = T + fyd
    w = Q(100.0, Kind.LENGTH)
    assert ((w * w) ** 0.5).expect(Kind.LENGTH).v == pytest.approx(100.0)


def test_bar_properties():
    assert bar_area(20) == pytest.approx(314.159, rel=1e-5)
    assert bar_unit_mass(20) == pytest.approx(2.466, rel=1e-3)   # kg/m


def test_fmt():
    assert fmt(12500.0, Kind.FORCE) == "12.5 kN"
    assert fmt(None, Kind.FORCE) == "—"
