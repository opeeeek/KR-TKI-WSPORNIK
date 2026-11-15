import pytest

from kwst.core.model import Variant, LoadAction, LoadCombination, NormativeInput
from kwst.load_engine import evaluate_combinations, import_actions_csv, export_actions_csv
from kwst.normative_parameters import get_parameter_set


def _ps():
    return get_parameter_set(NormativeInput())


def test_combinations_610ab():
    v = Variant()
    v.loads.actions = [LoadAction(name="G", category="G", V=180e3), LoadAction(name="Q", category="Q_B", V=120e3)]
    combos, msgs, _ = evaluate_combinations(v.loads, v.geometry, _ps())
    assert not msgs
    by = {c.name: c for c in combos}
    assert by["SGN (6.10a)"].sides["R"].V == pytest.approx(1.35 * 180e3 + 1.5 * 0.7 * 120e3)
    assert by["SGN Q (6.10b)"].sides["R"].V == pytest.approx(0.85 * 1.35 * 180e3 + 1.5 * 120e3)
    assert by["SGU quasi-stała (6.16b)"].sides["R"].V == pytest.approx(180e3 + 0.3 * 120e3)


def test_combination_610():
    v = Variant()
    v.loads.settings.method = "6.10"
    v.loads.actions = [LoadAction(name="G", category="G", V=100e3), LoadAction(name="Q1", category="Q_B", V=50e3),
                       LoadAction(name="S", category="S", V=20e3)]
    combos, _, _ = evaluate_combinations(v.loads, v.geometry, _ps())
    c = next(c for c in combos if c.name == "SGN Q1 (6.10)")
    assert c.sides["R"].V == pytest.approx(1.35 * 100e3 + 1.5 * 50e3 + 1.5 * 0.5 * 20e3)


def test_design_values_not_refactored():
    v = Variant()
    v.loads.actions = [LoadAction(name="Ed", nature="design", category="G", V=500e3, H=50e3)]
    combos, msgs, _ = evaluate_combinations(v.loads, v.geometry, _ps())
    assert not [m for m in msgs if m.level.value == "BŁĄD"]
    uls = [c for c in combos if c.is_uls]
    assert len(uls) == 1 and uls[0].kind == "ULS_DIRECT"
    assert uls[0].sides["R"].V == pytest.approx(500e3)   # bez γ
    assert uls[0].sides["R"].H == pytest.approx(50e3)


def test_double_factoring_blocked():
    v = Variant()
    v.loads.actions = [LoadAction(name="Ed", nature="design", category="G", V=500e3)]
    v.loads.combination_mode = "manual"
    v.loads.combinations = [LoadCombination("zła", "ULS", {"Ed": 1.35})]
    _, msgs, _ = evaluate_combinations(v.loads, v.geometry, _ps())
    assert any("ponowne stosowanie" in m.text or "podwójnego" in m.text for m in msgs)


def test_h_min_requires_source():
    v = Variant()
    v.loads.settings.H_min_enabled = True
    v.loads.settings.H_min_source = ""
    _, msgs, _ = evaluate_combinations(v.loads, v.geometry, _ps())
    assert any("źródła" in m.text for m in msgs)
    v.loads.settings.H_min_source = "Założenie projektanta wg literatury"
    v.loads.actions = [LoadAction(name="G", category="G", V=100e3)]
    combos, msgs, _ = evaluate_combinations(v.loads, v.geometry, _ps())
    c = next(c for c in combos if c.is_uls)
    assert c.sides["R"].H == pytest.approx(0.2 * c.sides["R"].V)
    assert c.sides["R"].H_min_applied


def test_eccentricity_and_moment_resultant():
    v = Variant()
    v.loads.actions = [LoadAction(name="Ed", nature="design", category="G", V=200e3, M=4e6, e_x=10.0, e_y=20.0)]
    combos, _, _ = evaluate_combinations(v.loads, v.geometry, _ps())
    s = combos[0].sides["R"]
    assert s.e_x == pytest.approx((4e6 + 200e3 * 10) / 200e3)
    assert s.e_y == pytest.approx(20.0)


def test_csv_roundtrip():
    acts = [LoadAction(name="G1", category="G", V=100e3, H=5e3), LoadAction(name="Q1", category="Q_A", V=50e3)]
    text = export_actions_csv(acts)
    back = import_actions_csv(text)
    assert [a.name for a in back] == ["G1", "Q1"]
    assert back[0].V == pytest.approx(100e3) and back[0].H == pytest.approx(5e3)
