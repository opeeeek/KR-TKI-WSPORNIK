"""Weryfikacja generatora modelu J.5 niezależnymi obliczeniami ręcznymi."""
import math
import pytest

from kwst.core.model import StmSettings
from kwst.geometry_engine import build_geometry
from kwst.load_engine import evaluate_combinations
from kwst.material_engine import build_materials
from kwst.normative_parameters import get_parameter_set
from kwst.stm_generator import build_corbel_model
from tests.helpers import direct_variant


def _setup(node_b="face", V=400e3, H=80e3):
    v = direct_variant(V=V, H=H, h_c=500.0, h_e=500.0, l_c=400.0, a_c=200.0)
    v.geometry.right.plate.length = 150.0
    v.geometry.right.plate.width = 300.0
    v.geometry.right.plate.thickness = 20.0
    ps = get_parameter_set(v.normative)
    mats = build_materials(v.materials, ps)
    gm = build_geometry(v.geometry)
    combos, _, _ = evaluate_combinations(v.loads, v.geometry, ps)
    st = StmSettings(lever_arm="user", node_b_position=node_b)
    return gm, combos[0], mats, ps, st


def test_face_mode_matches_J5_formula():
    gm, c, mats, ps, st = _setup("face")
    r = build_corbel_model(gm, c, mats, ps, st, 50.0, 1500.0, False, {"R": {"x_c_user": 100.0}})
    s = r.sides["R"].state
    # ręcznie: d = 450, z0 = d − x_c/2 = 400, a_H = c_t + t_p = 70
    z0, aH = 400.0, 70.0
    T_hand = 400e3 * 200.0 / z0 + 80e3 * (aH + z0) / z0          # rys. J.5
    assert s.z0 == pytest.approx(z0)
    assert s.T == pytest.approx(T_hand, rel=1e-12)
    assert r.solution.forces["TR"] == pytest.approx(T_hand, rel=1e-9)      # solver macierzowy
    xi_A = 200.0 + 80e3 * aH / 400e3
    assert s.C == pytest.approx(math.hypot(400e3 * xi_A / z0, 400e3), rel=1e-12)
    assert math.tan(s.theta) == pytest.approx(z0 / xi_A)
    assert r.comparison["max_rel_diff"] < 1e-9
    assert r.solution.equilibrium_ok


def test_in_column_mode_moment_equilibrium():
    gm, c, mats, ps, st = _setup("in_column")
    r = build_corbel_model(gm, c, mats, ps, st, 50.0, 1500.0, False, {"R": {"x_c_user": 100.0}})
    s = r.sides["R"].state
    z0 = 400.0
    xi_A = 200.0 + 80e3 * 70.0 / 400e3
    Fc = 400e3 / (2 * z0) * (xi_A + math.sqrt(xi_A ** 2 + 2 * 100.0 * z0))
    assert s.Fc == pytest.approx(Fc, rel=1e-12)
    assert s.a_B == pytest.approx(100.0 * 400e3 / Fc)
    # równowaga momentów względem węzła B
    lhs = s.T * z0
    rhs = 400e3 * (xi_A + s.a_B / 2.0) + 80e3 * z0
    assert lhs == pytest.approx(rhs, rel=1e-12)
    # węzeł hydrostatyczny: równe naprężenia na ściankach
    t = s.Fc / (s.x_c * 400.0)
    assert 400e3 / (s.a_B * 400.0) == pytest.approx(t)
    assert s.C / (s.w_B * 400.0) == pytest.approx(t)


def test_strut_width_and_bearing_stress():
    gm, c, mats, ps, st = _setup("face")
    r = build_corbel_model(gm, c, mats, ps, st, 50.0, 1500.0, False, {"R": {"x_c_user": 100.0}})
    s = r.sides["R"].state
    p = r.sides["R"].params
    # a_ef: wypadkowa przesunięta o H·t_p/V = 80·20/400 = 4 mm względem środka płyty
    assert p.a_ef == pytest.approx(150.0 - 2 * 4.0)
    assert s.w_A == pytest.approx(p.a_ef * math.sin(s.theta) + 100.0 * math.cos(s.theta))
    assert s.sigma_bearing == pytest.approx(400e3 / (p.a_ef * 300.0))


def test_optimal_lever_arm_not_worse_than_user():
    gm, c, mats, ps, st = _setup("in_column")
    st_opt = StmSettings(lever_arm="optimal")
    r_opt = build_corbel_model(gm, c, mats, ps, st_opt, 50.0, 1500.0, False)
    for xc in (40.0, 80.0, 150.0, 250.0):
        r_u = build_corbel_model(gm, c, mats, ps, st, 50.0, 1500.0, False, {"R": {"x_c_user": xc}})
        assert r_opt.sides["R"].state.eta_max() <= r_u.sides["R"].state.eta_max() + 1e-9


def test_design_mode_concrete_limit():
    gm, c, mats, ps, _ = _setup("in_column")
    r = build_corbel_model(gm, c, mats, ps, StmSettings(), 50.0, None, True)
    s = r.sides["R"].state
    assert s.eta_concrete() <= 1.0 + 1e-9
    assert 1.0 <= s.tan_theta <= 2.5
