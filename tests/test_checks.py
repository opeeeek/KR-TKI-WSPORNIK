"""Sprawdzenia elementarne — porównanie z niezależnymi obliczeniami ręcznymi."""
import math
import pytest

from kwst.anchorage_engine import AnchorageInput, anchorage_length, mandrel_checks, welded_bar_capacity
from kwst.core.model import MaterialsInput, NormativeInput
from kwst.material_engine import build_materials
from kwst.normative_parameters import get_parameter_set
from kwst.reinforcement_design import cover_requirements, vrdc, main_layout, s_min
from kwst.strut_checks import splitting_force
from kwst.core.units import bar_area


@pytest.fixture
def env():
    ps = get_parameter_set(NormativeInput())
    return ps, build_materials(MaterialsInput(), ps)


def test_anchorage_straight_hand(env):
    ps, m = env
    As = 3 * bar_area(20)
    a = AnchorageInput("X", "x", 20.0, As, As * m.steel.fyd, "straight", 1000.0, a_clear=100.0, c1=50.0, c=40.0)
    r = anchorage_length(a, m, ps)
    fbd = 2.25 * 0.7 * 1.0 * (2.0 / 1.4)
    lb_rqd = 20 / 4 * (500 / 1.15) / fbd
    assert r.fbd == pytest.approx(fbd)
    assert r.lb_rqd == pytest.approx(lb_rqd)
    assert r.alphas["α2"] == pytest.approx(1 - 0.15 * (40 - 20) / 20)
    assert r.lbd == pytest.approx(0.85 * lb_rqd)


def test_anchorage_minimum_length(env):
    ps, m = env
    a = AnchorageInput("X", "x", 16.0, 1000.0, 1.0, "straight", 1000.0, a_clear=100.0, c1=50.0, c=40.0)
    r = anchorage_length(a, m, ps)
    assert r.lbd == pytest.approx(max(10 * 16, 100.0))


def test_anchorage_bend_alpha1(env):
    ps, m = env
    # c_d = min(a/2, c1) = 70 > 3φ = 48 → α1 = 0,7
    a = AnchorageInput("X", "x", 16.0, 804.0, 804.0 * 434.78, "bend_down", 1000.0, a_clear=140.0, c1=80.0, c=40.0,
                       bond="good")
    r = anchorage_length(a, m, ps)
    assert r.alphas["α1"] == pytest.approx(0.7)
    assert r.alphas["α2"] == pytest.approx(max(0.7, 1 - 0.15 * (70 - 48) / 16))


def test_mandrel_formula_8_1(env):
    ps, m = env
    cs = mandrel_checks("M", "t", 20.0, 250.0, 100e3, 50.0, m, ps, "", "")
    req = 100e3 * (1 / 50 + 1 / 40) / (30 / 1.4)
    c81 = next(c for c in cs if c.id == "M_81")
    assert c81.E_d == pytest.approx(req)
    assert c81.status.value == "SPEŁNIONO"
    t81 = next(c for c in cs if c.id == "M_T81")
    assert t81.E_d == pytest.approx(140.0)


def test_welded_bar_8_8N(env):
    ps, m = env
    a = AnchorageInput("W", "w", 16.0, 804.0, 0.0, "welded_bar", 200.0, a_clear=80.0, c1=50.0, c=45.0, phi_t=16.0,
                       s_cc=96.0)
    F, _ = welded_bar_capacity(a, m, ps)
    x = 2 * 45 / 16 + 1
    y = 0.015 + 0.14 * math.exp(-0.18 * x)
    std = min((2.0 / 1.4) / y, 3 * 30 / 1.4)
    ltd = min(1.16 * 16 * math.sqrt((500 / 1.15) / std), 96.0)
    assert F == pytest.approx(min(ltd * 16 * std, 0.5 * bar_area(16) * 500 / 1.15))


def test_splitting_force():
    assert splitting_force(500e3, 100.0, 300.0, 1000.0)[0] == pytest.approx(0.25 * 200 / 300 * 500e3)
    assert splitting_force(500e3, 100.0, 800.0, 1000.0)[0] == pytest.approx(0.25 * (1 - 0.7 * 100 / 500) * 500e3)


def test_vrdc_hand(env):
    ps, m = env
    V, _ = vrdc(400.0, 450.0, 1500.0, 0.0, 500.0, m, ps)
    k = 1 + math.sqrt(200 / 450)
    v = 0.18 / 1.4 * k * (100 * 1500 / (400 * 450) * 30) ** (1 / 3)
    assert V == pytest.approx(v * 400 * 450)


def test_cover_xc1_s4(env):
    ps, _ = env
    cv = cover_requirements(MaterialsInput(exposure="XC1", structural_class="S4"), ps, 20.0, 10.0, 8.0, False, True)
    assert cv.c_min_dur == 15.0
    assert cv.c_nom_req_main == pytest.approx(30.0)
    assert cv.c_top_main >= cv.c_nom_req_main     # pręty główne zewnętrzne od góry
    assert cv.c_side_main >= cv.c_nom_req_main
    assert cv.c_nom >= cv.c_nom_req_link


def test_layout_spacing(env):
    ps, _ = env
    cv = cover_requirements(MaterialsInput(), ps, 20.0, 10.0, 8.0, False, True)
    ml = main_layout(400.0, cv, 20.0, 4, 1, None, 16.0, ps)
    assert ml.a_clear == pytest.approx((400 - 2 * cv.c_side_main - 4 * 20) / 3)
    assert ml.s_min == pytest.approx(s_min(20.0, 16.0, ps)) == pytest.approx(21.0 if 16 + 5 > 20 else 20.0)
    assert ml.fits
    bad = main_layout(400.0, cv, 25.0, 10, 1, None, 16.0, ps)
    assert not bad.fits
