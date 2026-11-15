import math
import pytest

from kwst import stm_solver as ss


def _corbel_truss(F=100e3, a=300.0, z=400.0):
    t = ss.TrussModel()
    t.nodes = [ss.TrussNode("A", a, 0.0), ss.TrussNode("B", 0.0, -z), ss.TrussNode("C", -200.0, 0.0)]
    t.members = [ss.TrussMember("S", "A", "B"), ss.TrussMember("T", "A", "C")]
    t.supports = [ss.TrussSupport("B"), ss.TrussSupport("C")]
    t.loads = [ss.TrussLoad("A", 0.0, -F)]
    return t


def test_two_bar_analytical():
    F, a, z = 100e3, 300.0, 400.0
    sol = ss.solve(_corbel_truss(F, a, z))
    assert sol.status == "determinate"
    # niezależnie: T = F·a/z, C = F/sin θ
    assert sol.forces["T"] == pytest.approx(F * a / z)
    assert -sol.forces["S"] == pytest.approx(F * math.hypot(a, z) / z)
    assert sol.equilibrium_ok
    assert abs(sol.global_residual[2]) < 1e-3


def test_mechanism_detected():
    t = _corbel_truss()
    t.supports = [ss.TrussSupport("B", True, False), ss.TrussSupport("C", True, False)]
    sol = ss.solve(t)
    assert sol.status == "mechanism"
    assert not sol.stable


def test_indeterminate_stiffness_matches_symmetry():
    # pręt podparty na obu końcach + pręt środkowy pionowy (układ niewyznaczalny)
    t = ss.TrussModel()
    t.nodes = [ss.TrussNode("L", -1000, 0), ss.TrussNode("R", 1000, 0), ss.TrussNode("M", 0, -500),
               ss.TrussNode("T", 0, 500)]
    t.members = [ss.TrussMember("LM", "L", "M", EA=1e8), ss.TrussMember("RM", "R", "M", EA=1e8),
                 ss.TrussMember("TM", "T", "M", EA=1e8)]
    t.supports = [ss.TrussSupport("L"), ss.TrussSupport("R"), ss.TrussSupport("T")]
    t.loads = [ss.TrussLoad("M", 0.0, -100e3)]
    sol = ss.solve(t)
    assert sol.status == "indeterminate" and sol.method == "stiffness"
    assert sol.forces["LM"] == pytest.approx(sol.forces["RM"], rel=1e-9)
    assert sol.equilibrium_ok


def test_invalid_models():
    t = _corbel_truss()
    t.members.append(ss.TrussMember("X", "A", "A"))
    with pytest.raises(ss.StmModelError):
        ss.solve(t)
    t = _corbel_truss()
    t.loads.append(ss.TrussLoad("Z", 1, 1))
    with pytest.raises(ss.StmModelError):
        ss.solve(t)
